import serial
import pynmea2
import time

filename = time.strftime("surface_data_%Y%m%d.sfc")
file = open(filename,'a')

wxt = serial.Serial('COM1', 19200, timeout=1.0)  # open wxt536 serial port
gps = serial.Serial('COM18', 19200, timeout=1.0)  # open arduino combo device
#print(wxt.name)         # check which port was really used

while True:

    filename = time.strftime("surface_data_%Y%m%d.sfc")
    file = open(filename, 'a')

    while (wxt.in_waiting):
        x = wxt.readline()
        print (x.decode("utf-8"),end="")
        file.write(x.decode("utf-8"))

    while (gps.in_waiting):
        x = gps.readline()
        print (x.decode("utf-8"),end="")
        file.write(x.decode("utf-8"))

    file.close()

# sadly we never get here :(
file.close()
wxt.close()
gps.close()

