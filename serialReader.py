import serial
import pynmea2

wxt = serial.Serial('COM1', 19200, timeout=0.25)  # open wxt536 serial port
gps = serial.Serial('COM5', 19200, timeout=0.25)  # open arduino combo device
#print(wxt.name)         # check which port was really used

while True:

    while (wxt.in_waiting):
        x = wxt.readline()
        print (x.decode("utf-8"),end="")

    while (gps.in_waiting):
        x = gps.readline()
        print (x.decode("utf-8"),end="")

# sadly we never get here :(
wxt.close()
gps.close()

