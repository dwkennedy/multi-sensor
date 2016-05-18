import serial
import pynmea2

file = open("surface_data.txt",'a')

wxt = serial.Serial('COM1', 19200, timeout=0.25)  # open wxt536 serial port
gps = serial.Serial('COM5', 19200, timeout=0.25)  # open arduino combo device
#print(wxt.name)         # check which port was really used

while True:

    while (wxt.in_waiting):
        x = wxt.readline()
        print (x.decode("utf-8"),end="")
        file.write(x.decode("utf-8"))

    while (gps.in_waiting):
        x = gps.readline()
        print (x.decode("utf-8"),end="")
        file.write(x.decode("utf-8"))

    file.close()
    file = open("surface_data.txt",'a')

# sadly we never get here :(
file.close()
wxt.close()
gps.close()

