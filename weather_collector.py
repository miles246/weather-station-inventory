#!/usr/bin/env python3
"""
All-sky weather station collector - Raspberry Pi port of w2.ino

Reads I2C sensors (BME280, MLX90614, TSL2591, LTR390 UV when added, and an
optional ENS160 air-quality sensor for bench testing), computes dew point +
heat index, and writes everything to InfluxDB 2.x on a fixed interval.

Sensors / I2C addresses (all share one bus):
    BME280    0x76 or 0x77 (SparkFun board = 0x77)  - temp / humidity / pressure
    MLX90614  0x5a                                   - sky IR temp / cloud
    TSL2591   0x29                                   - sky quality / lux
    LTR390    0x53                                   - UV (added later)
    ENS160    0x53                                   - air quality (TEST ONLY*)

* ENS160 and LTR390 share 0x53, so only one of them is on the bus at a time.
  ENS160 is just for validating the pipeline before the real sensors arrive.
"""

import math
import time
import logging

import board
import busio

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# ----------------------------------------------------------------------------
# Configuration  --  EDIT THESE
# ----------------------------------------------------------------------------
INFLUX_URL    = "http://localhost:8086"
INFLUX_TOKEN  = "wx-20821c1ce963c64ee0627e00bc5698aed787002c1b10a03b"
INFLUX_ORG    = "home"
INFLUX_BUCKET = "weather"

MEASUREMENT   = "allsky"
STATION_TAG   = "weatherstation1"
READ_INTERVAL = 10                # seconds
SEALEVELPRESSURE_HPA = 1013.25

# BME280 address: SparkFun combo board = 0x77, most purple breakouts = 0x76
BME280_ADDRESS = 0x76  # standalone BME280 (radiation shield)

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("weather")


# ----------------------------------------------------------------------------
# Math ported from weatherCalcs.cpp
# ----------------------------------------------------------------------------
def dew_point_c(temp_c, humidity):
    a, b = 17.62, 243.12
    gamma = (a * temp_c) / (b + temp_c) + math.log(humidity / 100.0)
    return (b * gamma) / (a - gamma)


def heat_index_c(temp_c, humidity):
    t = temp_c * 9.0 / 5.0 + 32.0
    r = humidity
    hi = 0.5 * (t + 61.0 + ((t - 68.0) * 1.2) + (r * 0.094))
    if hi > 80.0:
        hi = (-42.379 + 2.04901523 * t + 10.14333127 * r
              - 0.22475541 * t * r - 6.83783e-3 * t * t
              - 5.481717e-2 * r * r + 1.22874e-3 * t * t * r
              + 8.5282e-4 * t * r * r - 1.99e-6 * t * t * r * r)
    return (hi - 32.0) * 5.0 / 9.0


def cloud_index(sky_obj_c, ambient_c):
    return ambient_c - sky_obj_c


def mpsas_from_lux(lux):
    if lux is None or lux <= 0:
        return None
    return 12.6 - 2.5 * math.log10(lux)


# ----------------------------------------------------------------------------
# Sensor setup  --  each guarded so one missing/dead sensor won't kill the rest
# ----------------------------------------------------------------------------
i2c = busio.I2C(board.SCL, board.SDA)
bme = mlx = tsl = uv = ens = None

try:
    from adafruit_bme280 import basic as adafruit_bme280
    bme = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=BME280_ADDRESS)
    bme.sea_level_pressure = SEALEVELPRESSURE_HPA
    log.info("BME280 ready @ 0x%02x", BME280_ADDRESS)
except Exception as e:
    log.warning("BME280 not found: %s", e)

try:
    import adafruit_mlx90614
    mlx = adafruit_mlx90614.MLX90614(i2c)
    log.info("MLX90614 ready")
except Exception as e:
    log.warning("MLX90614 not found: %s", e)

try:
    import adafruit_tsl2591
    tsl = adafruit_tsl2591.TSL2591(i2c)
    tsl.gain = adafruit_tsl2591.GAIN_LOW
    tsl.integration_time = adafruit_tsl2591.INTEGRATIONTIME_200MS
    log.info("TSL2591 ready")
except Exception as e:
    log.warning("TSL2591 not found: %s", e)

try:
    import adafruit_ltr390
    uv = adafruit_ltr390.LTR390(i2c)
    log.info("LTR390 (UV) ready")
except Exception as e:
    log.info("LTR390 (UV) not present yet - will activate when added")

# Optional ENS160 air-quality sensor (SparkFun combo) - bench testing only.
try:
    import adafruit_ens160
    ens = adafruit_ens160.ENS160(i2c)
    log.info("ENS160 (air quality) ready - test sensor")
except Exception as e:
    log.info("ENS160 not present (fine - it's test-only)")


def read_all():
    fields = {}
    if bme:
        fields["temp"]     = float(bme.temperature)
        fields["pressure"] = float(bme.pressure)
        fields["humidity"] = float(bme.humidity)
    if mlx:
        fields["mlx_temp_amb"] = float(mlx.ambient_temperature)
        fields["mlx_temp_obj"] = float(mlx.object_temperature)
        fields["cloud_index"]  = cloud_index(fields["mlx_temp_obj"],
                                             fields["mlx_temp_amb"])
    if tsl:
        fields["full"] = int(tsl.full_spectrum)
        fields["ir"]   = int(tsl.infrared)
        fields["vis"]  = int(tsl.visible)
        try:
            lux = float(tsl.lux)
            fields["lux"] = lux
            m = mpsas_from_lux(lux)
            if m is not None:
                fields["mpsas"] = m
        except Exception:
            pass
    if uv:
        try:
            fields["uv_index"] = float(uv.uvi)
            fields["uv_light"] = float(uv.light)
        except Exception as e:
            log.warning("LTR390 read failed: %s", e)
    if ens:
        try:
            fields["aqi"]  = int(ens.AQI)
            fields["tvoc"] = int(ens.TVOC)
            fields["eco2"] = int(ens.eCO2)
        except Exception:
            pass
    if "temp" in fields and "humidity" in fields:
        fields["dewpoint"]   = dew_point_c(fields["temp"], fields["humidity"])
        fields["heat_index"] = heat_index_c(fields["temp"], fields["humidity"])
    return fields


def main():
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    write_api = client.write_api(write_options=SYNCHRONOUS)
    log.info("Writing to InfluxDB %s bucket=%s every %ss",
             INFLUX_URL, INFLUX_BUCKET, READ_INTERVAL)
    try:
        while True:
            fields = read_all()
            if fields:
                point = Point(MEASUREMENT).tag("station", STATION_TAG)
                for k, v in fields.items():
                    point = point.field(k, v)
                try:
                    write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
                    log.info("wrote %d fields: %s", len(fields),
                             {k: round(v, 2) if isinstance(v, float) else v
                              for k, v in fields.items()})
                except Exception as e:
                    log.error("InfluxDB write failed: %s", e)
            else:
                log.warning("no sensors returned data - check i2cdetect -y 1")
            time.sleep(READ_INTERVAL)
    except KeyboardInterrupt:
        log.info("stopping")
    finally:
        client.close()


if __name__ == "__main__":
    main()
