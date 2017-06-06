import http.server
import socketserver
import json
import threading
import time
import sys
import serial
import pynmea2
import geomag
import random
from os import rename

PORT = 8000
temp = -999.0
press = -999.0
RH = -999.0
wind_spd = -999.0
wind_dir = -999.0
win_dir_nose_rel = -999.0
mag_heading = -999.0
true_heading = -999.0
declination = 0
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
                                 "mag_heading": mag_heading, "true_heading": true_heading, "declination": declination,
                                 "roll": roll, "pitch": pitch, "lat":lat, "lon":lon, "course":course, "spd":spd, "alt":alt})
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
        global temp, press, RH, wind_spd, wind_dir, mag_heading, true_heading, declination
        global roll, pitch, lat, lon, course, spd, alt, wind_dir_nose_rel

        Handler = MyHTTPRequestHandler
        httpd = socketserver.TCPServer(("", PORT), Handler)

        print("serving at port", PORT)
        httpd.serve_forever()

class Thread_B(threading.Thread):
    def __init__(self, name):
        threading.Thread.__init__(self)
        self.name = name

    def run(self):
        global temp, press, RH, wind_spd, wind_dir, mag_heading, true_heading, declination
        global roll, pitch, lat, lon, course, spd, alt
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

                try:
                    msg = pynmea2.parse(x.decode("utf-8"))
                    if msg.talker == 'WI':
                        if msg.sentence_type == 'MWV':
                            wind_dir_nose_rel = float(msg.data[0])
                            wind_dir = float(msg.data[0]) + mag_heading + declination
                            if wind_dir < 0:
                                wind_dir = -999.0
                            if wind_dir > 360.0:
                                wind_dir -= 360.0
                            wind_spd = float(msg.data[2])
                            #print (msg)
                            msg.data[0] = str(round(wind_dir))
                            #print (msg)
                            x = (str(msg)+'\n').encode("utf-8")
                            mwvValid = time.time()

                            print("Wind Direction (deg): %.1f  Wind Speed (m/s): %.1f  Nose Rel (deg): %.1f  Data Status (A=valid): %s"
                                  % (wind_dir, wind_spd, wind_dir_nose_rel, msg.data[4]))
                except:
                    pass

                try:
                    msg = pynmea2.parse(x.decode("utf-8"))
                    if msg.talker == 'WI':
                        if msg.sentence_type == 'XDR':
                            if (msg.data[0] == 'C' and int(msg.data[3]) == 0):  # temp, humidity, pressure message
                                # print(line)
                                temp = float(msg.data[1])
                                RH = float(msg.data[5])
                                press = float(msg.data[9])
                                xdrValid = time.time()
                                print("\nTemp (C): %.1f  RH: %.1f  Pressure (hPa): %.1f" % (temp, RH, press))
                                #SASSI = "CLMP %f %f %s %s %s %s %s %s %s %s" % (lat, lon, course, spd, temp, temp, RH, press, wind_dir, wind_spd)
                                #print(SASSI)
                                #tmpFilename = "C:\\Users\\FOFS\\AppData\\Local\\Rasmussen Systems\\SASSI\\Outgoing\\%d.mmm" % int(time.time())
                                #sassiFilename = "C:\\Users\\FOFS\\AppData\\Local\\Rasmussen Systems\\SASSI\\Outgoing\\%d.mmm" % int(time.time())
                                #print(sassiFilename)
                                #try:
                                #    sassiFile = open(tmpFilename, 'w')
                                #except:
                                #    print("Couldn't write SASSI file to " + tmpFilename)
                                 #   pass
                                #sassiFile.write(SASSI)
                                #sassiFile.close()
                                #try:
                                #    os.rename(tmpFilename, sassiFilename);
                                #except:
                                #    print("Couldn't rename %s to %s" % (tmpFilename, sassiFilename));
                except:
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
                        roll = float(msg.data[1])
                        pitch = float(msg.data[2])
                        mag_heading = float(msg.data[3])
                        true_heading = mag_heading + declination
                        print("Mag heading: %.2f True heading: %.2f Roll: %.2f Pitch: %.2f" % (mag_heading, true_heading, roll, pitch))
                except:
                    #print("PCLMP parse error")
                    pass

                try:
                    msg = pynmea2.parse(x.decode("utf-8"))
                    if msg.talker == 'GP':  # decode GPRMC and GPGGA here.  update time/date variables
                        if msg.sentence_type == 'RMC':
                            if msg.data[1] == 'A':
                                spd = float(msg.data[6])
                                course = float(msg.data[7])
                                lat = msg.latitude
                                lon = msg.longitude
                                if alt == -999.0:
                                    pass
                                    declination = geomag.declination(lat,lon)
                                else:
                                    pass
                                    declination = geomag.declination(lat,lon,alt)
                                #lat = 35
                                #lon = -97.5
                            else:
                                spd = -999.0
                                course = -999.0
                                # generate test locations when gps is not locked
                                #lat = 35 + random.random()
                                #lon = -97 + random.random()
                except:
                    pass
                    #print("GPRMC parse error")

                try:
                    msg = pynmea2.parse(x.decode("utf-8"))
                    if msg.talker == 'GP':

                        if msg.sentence_type == 'GGA':
                            if msg.gps_qual > 0:
                                alt = msg.altitude
                            else:
                                alt = -999.0
                                #msg = pynmea2.GGA('GP', 'GGA', (
                                #'184353.07', '1929.045', 'S', '02410.506', 'E', '1', '04', '2.6', '100.00', 'M',
                                #'-33.9', 'M', '', '0000')
                except:
                    #print("GPGGA parse error")
                    pass

                print(x.decode("utf-8"), end="")
                file.write(x.decode("utf-8") + '\n')


a = Thread_A("myThread_name_A")
b = Thread_B("myThread_name_B")

b.start()
a.start()

a.join()
b.join()