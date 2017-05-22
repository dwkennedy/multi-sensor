import http.server
import socketserver
import json
import threading
import time
import sys
import serial
import pynmea2

PORT = 8000
temp = -999.0
press = -999.0
RH = -999.0
wind_spd = -999.0
wind_dir = -999.0

class MyHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type','text/html')
        self.end_headers()
        self.flush_headers()
        if self.path == '/':
            f = open("sfc_template.html")
            string = f.read()
            self.wfile.write(string.encode('utf-8'))
        elif self.path == '/data':
            string = json.dumps({"temp": temp, "press": press, "RH": RH, "wind_spd": wind_spd, "wind_dir": wind_dir})
            self.wfile.write(string.encode('utf-8'))
            #self.wfile.write(self.path.encode('utf-8'))
        elif self.path == '/favicon.ico':
            f = open("favicon.ico", 'rb')
            string = f.read()
            self.wfile.write(string)
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
        global temp, press, RH, wind_spd, wind_dir
        filename = time.strftime("surface_data_%Y%m%d.sfc")
        print("Opening new file: ", filename)
        file = open(filename, 'a')

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

                            print("\nWind Direction (deg): " + wind_dir + "  Wind Speed (m/s): " + wind_spd
                                  + "  Data Status (A=valid): " + msg.data[4])
                except:
                    msg = pynmea2.parse(line)
                    pass

                try:
                    if msg.talker == 'WI':
                        if msg.sentence_type == 'XDR':
                            # print (msg.data[0],msg.data[3])
                            if (msg.data[0] == 'C' and int(msg.data[3]) == 0):  # temp, humidity, pressure message
                                # print(line)
                                temp = msg.data[1]
                                RH = msg.data[5]
                                press = msg.data[9]
                                print("\nTemp (C): " + temp + "  RH (%): " + RH + "  Pressure (hPa): " +
                                      press)
                except:
                    msg = pynmea2.parse(line)
                    pass

                try:
                    if msg.talker == 'GP':  # decode GPRMC and GPGGA here.  update time/date variables
                        pass
                except:
                    pass

                print(x.decode("utf-8"), end="")
                file.write(x.decode("utf-8") + '\n')

            while (gps.in_waiting):
                x = gps.readline()
                print(x.decode("utf-8"), end="")
                file.write(x.decode("utf-8") + '\n')


a = Thread_A("myThread_name_A")
b = Thread_B("myThread_name_B")

b.start()
a.start()

a.join()
b.join()