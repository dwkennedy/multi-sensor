import http.server
import socketserver
import json
import threading
import time
import sys
import serial
import pynmea2
import random

PORT = 8000
temp = -999.0
press = -999.0
RH = -999.0
wind_spd = -999.0
wind_dir = -999.0
heading = -999.0
roll = -999.0
pitch = -999.0
lat = -999.0
lon = -999.0
course = -999.0
spd = -999.0
alt = -999.0


class MyHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        #self.send_header('Content-type','text/html')
        #self.end_headers()
        #self.flush_headers()
        if self.path == '/':
            f = open("sfc_template.html")
            string = f.read()
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.flush_headers()
            self.wfile.write(string.encode('utf-8'))
        elif self.path == '/data':
            string = json.dumps({"temp": temp, "press": press, "RH": RH, "wind_spd": wind_spd, "wind_dir": wind_dir,
                                 "heading": heading, "roll": roll, "pitch": pitch, "lat":lat, "lon":lon, "course":course,
                                 "spd":spd, "alt":alt})
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.flush_headers()
            self.wfile.write(string.encode('utf-8'))
            #self.wfile.write(self.path.encode('utf-8'))
        elif self.path == '/favicon.ico':
            f = open("favicon.ico", 'rb')
            string = f.read()
            self.send_header('Content-type', 'image/png')
            self.end_headers()
            self.flush_headers()
            self.wfile.write(string)
        elif self.path == '/loc.kml':
            string = ('<?xml version="1.0" encoding="UTF-8"?>'
                      '<kml xmlns="http://www.opengis.net/kml/2.2">'
                      '<Placemark>'
                      '<name>CLAMPS2</name>'
                      '<LookAt>'
                      '<longitude>%f</longitude>'
                      '<latitude>%f</latitude>'
                      '<range>5000</range>'
                      '<tilt>0</tilt>'
                      '</LookAt>'
                      '<Point>'
                      '<coordinates> %f,%f </coordinates>'
                      '</Point>'
                      '</Placemark>'
                      '</kml>'
                      ) % (lon, lat, lon, lat)
            self.send_header('Content-type', 'application/vnd.google-earth.kml+xml')
            self.end_headers()
            self.flush_headers()
            self.wfile.write(string.encode('utf-8'))

        return


class Thread_A(threading.Thread):
    def __init__(self, name):
        threading.Thread.__init__(self)
        self.name = name

    def run(self):
        global press
        global temp  # made global here
        global RH, wind_spd, wind_dir

        Handler = MyHTTPRequestHandler
        httpd = socketserver.TCPServer(("", PORT), Handler)

        print("serving at port", PORT)
        httpd.serve_forever()

class Thread_B(threading.Thread):
    def __init__(self, name):
        threading.Thread.__init__(self)
        self.name = name

    def run(self):
        global temp, press, RH, wind_spd, wind_dir, heading, roll, pitch, lat, lon, course, spd, alt
        filename = time.strftime("surface_data_%Y%m%d.sfc")
        print("Opening new file: ", filename)
        file = open(filename, 'a')
        xdrValid = 0
        mwvValid = 0

        wxt = serial.Serial('COM1', 19200, timeout=1.0)  # open wxt536 serial port
        gps = serial.Serial('COM18', 19200, timeout=1.0)  # open arduino combo device
        # print(wxt.name)         # check which port was really used

        while True:

            newFilename = time.strftime("surface_data_%Y%m%d.sfc")
            if newFilename != filename:
                file.close()
                filename = newFilename
                file = open(filename, 'a')
                print("Opening new file: ", filename)

            while (wxt.in_waiting):
                x = wxt.readline()
                msg = pynmea2.parse(x.decode("utf-8"))
                try:
                    if msg.talker == 'WI':
                        if msg.sentence_type == 'MWV':
                            wind_dir = msg.data[0]
                            wind_spd = msg.data[2]
                            mwvValid = time.time()

                            print("\nWind Direction (deg): " + wind_dir + "  Wind Speed (m/s): " + wind_spd
                                  + "  Data Status (A=valid): " + msg.data[4])
                except:
                    msg = pynmea2.parse(x.decode("utf-8"))
                    pass

                try:
                    if msg.talker == 'WI':
                        if msg.sentence_type == 'XDR':
                            if (msg.data[0] == 'C' and int(msg.data[3]) == 0):  # temp, humidity, pressure message
                                # print(line)
                                temp = msg.data[1]
                                RH = msg.data[5]
                                press = msg.data[9]
                                xdrValid = time.time()
                                print("\nTemp (C): %s  RH: %s  Pressure (hPa): %s" % (temp, RH, press))
                                SASSI = "CLMP %f %f %s %s %s %s %s %s %s %s" % (lat, lon, course, spd, temp, temp, RH, press, wind_dir, wind_spd)
                                print(SASSI)
                                sassiFilename = "C:\\Users\\FOFS\\AppData\\Local\\Rasmussen Systems\\SASSI\\Outgoing\\%d.mmm" % int(time.time())
                                print(sassiFilename)
                                try:
                                    sassiFile = open(sassiFilename, 'w')
                                except:
                                    print("Couldn't write SASSI file to " + sassiFilename)
                                    pass
                                sassiFile.write(SASSI)
                                sassiFile.close()
                except:
                    msg = pynmea2.parse(x.decode("utf-8"))
                    pass

                #print (msg.talker)
                print(x.decode("utf-8"), end="")
                file.write(x.decode("utf-8") + '\n')

            try:
                    if (time.time()-xdrValid ) > 120:
                       temp = -999.0
                       RH = -999.0
                       press = -999.0
            except:
                    print ("foo!")

            try:
                    if (time.time()-mwvValid) > 15:
                       wind_spd = -999.0
                       wind_dir = -999.0
            except:
                    print ("foo2!")

            while (gps.in_waiting):
                x = gps.readline()
                try:
                    msg = pynmea2.parse(x.decode("utf-8"))
                    #print(msg.talker)
                    if msg.manufacturer == 'CLM':
                        roll = msg.data[1]
                        pitch = msg.data[2]
                        heading = msg.data[3]
                        print("\nHeading (mag): " + heading + " Roll: " + roll + " Pitch: " + pitch)
                except:
                    #print("error")
                    pass

                try:
                    msg = pynmea2.parse(x.decode("utf-8"))
                    if msg.talker == 'GP':  # decode GPRMC and GPGGA here.  update time/date variables
                        if msg.sentence_type == 'RMC':
                            if msg.data[1] == 'A':
                                spd = msg.data[6]
                                course = msg.data[7]
                                lat = msg.latitude
                                lon = msg.longitude
                                #lat = 35
                                #lon = -97.5
                            else:
                                spd = -999.0
                                course = -999.0
                                # generate test locations when gps is not locked
                                #lat = 35 + random.random()
                                #lon = -97 + random.random()

                        if msg.sentence_type == 'GGA':
                            if msg.gps_qual > 0:
                                alt = msg.altitude
                            else:
                                alt = -999.0
                                #msg = pynmea2.GGA('GP', 'GGA', (
                                #'184353.07', '1929.045', 'S', '02410.506', 'E', '1', '04', '2.6', '100.00', 'M',
                                #'-33.9', 'M', '', '0000')
                except:
                    pass

                print(x.decode("utf-8"), end="")
                file.write(x.decode("utf-8") + '\n')


a = Thread_A("myThread_name_A")
b = Thread_B("myThread_name_B")

b.start()
a.start()

a.join()
b.join()