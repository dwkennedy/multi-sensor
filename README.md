# multi-sensor
Data logging from arduino leonardo with adafruit ultimate GPS and adafruit 10 DOF sensor board

Fetch with 'git clone https://github.com/dwkennedy/multi-sensor'
Then execute 'git submodule init' and 'git submodule update' to fetch all
geoidheight and geomag data

Arduino code
multi-sensor:  reads GPS on softwareserial and I2C 10DOF board, prints to USB serial
mutli-sensor-calib:  reads and averages 10DOF output for calibrating the magnetometer and accelerometer
magnetometer-calib:  reads the XYZ components of the magnetometer and the accelerometer, dumps in CSV.  Use R or something to find the min/max values and calculate the offset to normalize the data.  Don't need to scale the axes unless they are very different.
magnetometer-calib-check: read 1000 samples and average, compute the compass direction, and display.  To verify the calibration.

multi-sensor generates a proprietary NMEA-type sentence, in addition to GPRMC, GPGGA, and the WI (weather instrument) sentences from the WXT-536 instrument.

$PCLMP2,roll,pitch,heading,pressure,temp
P=proprietary
CLM=manufacturer
P2=platform ID
roll=attitude of vehicle, left to right
pitch=attitude of vehicle, front to back
heading=magnetic heading of tail of trailer
pressure, temp: from the BMP180 sensor

requirements:  adafruit 10DOF and GPS libraries

https://github.com/adafruit/Adafruit-GPS-Library
https://github.com/adafruit/Adafruit_Sensor
https://github.com/adafruit/Adafruit_10DOF
https://github.com/adafruit/Adafruit_LSM303DLHC
https://github.com/adafruit/Adafruit_L3GD20_U
https://github.com/adafruit/Adafruit_BMP085_Unified


Python code
serialReader.py: read from COM1 (Vaisala WXT536 all-in-one weather sensor) and COM18 (arduino logger), writing incoming lines to a single file  (Obsolete)

decodeGPS.py: read GPS and special NMEA sentences from arduino device, publish to MQTT topic gps/SERIAL_NUMBER

requirements: python 3.5+, pyserial, pynmea2, geomag libraries. use ubuntu apt-get to install python3-nmea2, python3-serial.  get geomag from https://github.com/chompar4/geomag.

obsolete: https://github.com/cmweiss/geomag https://pypi.python.org/pypi/geomag/
python3 compatible and WMM2020 coefficients --> https://github.com/chompar4/geomag

revision history:
Started around 5/18/2016 for CLAMPS2 trailer (v1.0)
Improvements made around 5/20/2017 for EPIC and RiVorS projects (v1.1)

V1.1 improvements:
Parse NMEA strings into human readable format
Expose web interface for present weather conditions and trailer orientation
Calibrated magnetometer, added code for compass heading

V2.0 improvements:
publish to MQTT
update geomag to WMM2020
all-around better error handling

TODO: (out of date)
Parse GPS messages and display date/time/location/elevation.
Include link to Google Maps/Google Earth
make nicer present weather display (text, or ultimately graphical; show recent history and trend

