# multi-sensor
Data logging from arduino leonardo with adafruit ultimate GPS and adafruit 10 DOF sensor board

Arduino code
multi-sensor:  reads GPS on softwareserial and I2C 10DOF board, prints to USB serial
mutli-sensor-calib:  reads and averages 10DOF output for calibrating the magnetometer and accelerometer

requirements:  adafruit 10DOF and GPS libraries

https://github.com/adafruit/Adafruit-GPS-Library
https://github.com/adafruit/Adafruit_Sensor
https://github.com/adafruit/Adafruit_10DOF
https://github.com/adafruit/Adafruit_LSM303DLHC
https://github.com/adafruit/Adafruit_L3GD20_U
https://github.com/adafruit/Adafruit_BMP085_Unified


Python code
serialReader.py: read from COM1 (Vaisala WXT536 all-in-one weather sensor) and COM5 (arduino logger), writing incoming lines to a single file

requirements: pyserial, pynmea2 libraries.  I like using PIP to install pynmea2

revision history:
Started around 5/18/2016 for CLAMPS2 trailer

TODO:
write strings into file (for init testing, writes to console)
close current file, open new file every hour
parse NMEA strings & weather strings
make present weather display (text, or ultimately graphical)

