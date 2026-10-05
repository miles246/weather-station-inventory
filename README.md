# All-Sky Weather Station Hardware Inventory

## Overview
Raspberry Pi 4-based weather station for all-sky observations at MSU Abrams Planetarium.
Host: `morp@192.168.68.112` (Tailscale: `weatherstation.tail0e4b3.ts.net`)

## Active Components (Confirmed)

| Component | I2C Address | Function | Status | Price |
|-----------|-------------|----------|--------|-------|
| BME280 | 0x76 | Temperature, Humidity, Barometric Pressure | ✅ Active | $10 |
| MLX90614 | 0x5a | IR Thermometer (Sky/Cloud Temperature) | ✅ Active | $15 |
| TSL2591 | 0x29 | Full-Spectrum Light Sensor (Lux, IR, Visible) | ✅ Active | $10 |
| All-Sky Camera | N/A | IR-sensitive camera for sky imaging | ✅ Active | $45 |
| Raspberry Pi Fan | N/A | Cooling for Pi + anti-dew for camera | ✅ Active | $13 |

## Pending/Optional Components

| Component | I2C Address | Function | Status | Notes |
|-----------|-------------|----------|--------|-------|
| LTR390 | 0x53 | UV Index Sensor | 🔴 Not Connected | Address shared with ENS160 |
| ENS160 | 0x53 | Air Quality Sensor (Test) | 🔴 Not Connected | Test-only, shared address |
| Radiation Shield | N/A | BME280 Protection | ⚠️ TBD | Box, Plugs, Glue, Dome ($75) |

## Already Owned (No Cost)

| Component | Notes |
|-----------|-------|
| Raspberry Pi 4 Model B (4GB) | Already owned |
| MicroSD Card (16GB+) | Already owned |
| Power Supply (5V/3A USB-C) | $10 |

## Hardware Specifications

### Main Controller
- **Model**: Raspberry Pi 4 Model B Rev 1.2
- **RAM**: 4GB (based on revision b03112)
- **OS**: Debian 13 Trixie (aarch64)
- **Serial**: 100000006c337908

### Software Stack
- **Data Collection**: Python 3 with Adafruit CircuitPython libraries
- **Database**: InfluxDB 2.9.1 (local)
- **Visualization**: Grafana
- **Collector Service**: `weather-collector.service`

## I2C Bus Scan Results
```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:                         -- -- -- -- -- -- -- -- 
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
20: -- -- -- -- -- -- -- -- -- 29 -- -- -- -- -- -- 
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
50: -- -- -- -- -- -- -- -- -- -- 5a -- -- -- -- -- 
60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
70: -- -- -- -- -- -- 76 --
```

**Note**: Camera is connected via CSI/USB (not I2C), so it doesn't appear in the I2C scan.

## Python Dependencies
```
adafruit-blinka
adafruit-circuitpython-bme280
adafruit-circuitpython-mlx90614
adafruit-circuitpython-tsl2591
adafruit-circuitpython-ltr390
adafruit-circuitpython-ens160
influxdb-client
```

## Grafana Dashboards
Grafana is running on the weather station and provides real-time visualization of sensor data.

**Access**: http://weatherstation:3000 (or http://192.168.68.112:3000)
- **Login**: admin / <GRAFANA_PASSWORD>

**Dashboards**:
- **Planetarium Detail** (`planetarium-detail.json`) - Comprehensive weather station overview
- **All-Sky Camera** (`allsky-camera.json`) - Camera and sky quality metrics

**Provisioning**:
- InfluxDB datasource configured with Flux query support
- Auto-provisioned from `/var/lib/grafana/dashboards/`
- Updates every 30 seconds

See `grafana/` directory for all dashboard JSON files and provisioning configs.

## Notes
- All I2C sensors share a single bus
- LTR390 and ENS160 share I2C address 0x53 (only one can be active at a time)
- ENS160 is for test-only pipeline validation
- **Camera**: IR-sensitive all-sky camera is now active (CSI or USB connection)
- **Fan**: Raspberry Pi fan serves dual purpose - cooling the Pi and anti-dew for the camera
- Radiation shield recommended for accurate temperature readings

## Reimbursement Summary
- **Active Components Total**: $93 (BME280 $10 + MLX90614 $15 + TSL2591 $10 + Camera $45 + Fan $13)
- **Pending**: Radiation Shield ($75)
- **Already Owned**: Raspberry Pi 4, MicroSD Card
- **Total Reimbursement Requested**: $93 (excluding items already owned)

See `Weather_Station_Inventory.xlsx` for the detailed inventory with pricing.

## Contact
fi23@msu.edu
