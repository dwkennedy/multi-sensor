#!/usr/bin/python3

# altitude is sum of geoidal seperation and ellipsoid altitude (ie. GPGGA provides an estimate of MSL as well as the undulation)
# https://gis.stackexchange.com/questions/174046/relation-between-geoidal-separation-and-antenna-altitude-in-gga-sentence

# read sentences from GPS (multi-sensor unit), decode, and publish to MQTT as JSON strings
#  /gps/SERIAL_NUMBER  (match serial to WXT unit in use)
# calculate true heading using GPS location and magnetic heading

import sys
import time
import datetime
from calendar import timegm
import json
import serial
import pynmea2
import geomag
import paho.mqtt.client as mqtt
import numpy as np

missing_values = {
   'time': -999.0,
   'gps_time': -999.0,
   'lat': -999.0,
   'lon': -999.0,
   'course': -999.0,
   'spd_kts': -999.0,
   'alt_msl': -999.0,
   'geo_sep': -999.0,
   'internal_pres': -999.0,
   'internal_temp': -999.0,
   'roll': -999.0,
   'pitch': -999.0,
   'mag_heading': -999.0,
   'true_heading': -999.0,
   'declination': -999.0,
}
"""

missing_values = {
   'time': np.nan,
   'gps_time': np.nan,
   'lat': np.nan,
   'lon': np.nan,
   'course': np.nan,
   'spd_kts': np.nan,
   'alt_msl': np.nan,
   'geo_sep': np.nan,
   'internal_pres': np.nan,
   'internal_temp': np.nan,
   'roll': np.nan,
   'pitch': np.nan,
   'mag_heading': np.nan,
   'true_heading': np.nan,
   'declination': np.nan,
}
"""

LOCAL_BROKER_ADDRESS = '127.0.0.1'  # MQTT broker address
REMOTE_BROKER_ADDRESS = 'kennedy.tw'  # remote MQTT broker address
WXT_SERIAL = 'N3720229' # PTU S/N N3620062
WXT_ELEVATION = 375.0   # WXT sensor elevation in meters above MSL
GPS_SERIAL_DEVICE = '/dev/ttyACM0'
GPS_BAUDRATE = 19200

# now we define the callbacks to handle messages we subcribed to
def on_message(client, userdata, message):
    print("message received: {0}".format(str(message.payload.decode("ISO-8859-1"))))
    print("message topic: {0}".format(message.topic))
    print("message qos: {0}".format(message.qos))
    print("message retain flag: {0}".format(message.retain))
    command = message.payload.decode('ISO-8859-1')
    print('{}: MQTT sub: {}: {}'.format(time.asctime(), message.topic, command))
    command += '\r\n'
    try:
        s.send(command.encode())
    except:
        print("{}: MQTT command send to GPS failed".format(time.asctime()))

def main():
        last_seen_rmc = datetime.time(0,0,2)
        last_seen_gga = datetime.time(0,0,1)
        current = missing_values  # we fill these in as we receive sentences

        client = mqtt.Client('pbx-gps')
        client.on_message = on_message
        client.connect(LOCAL_BROKER_ADDRESS)
        client.loop_start()
        client.subscribe('gps/{}/cmd'.format(WXT_SERIAL))  # subscribe to command channel

        gps = serial.Serial(GPS_SERIAL_DEVICE, GPS_BAUDRATE, timeout=1.0)  # open arduino combo device

        while True:

            if (gps.in_waiting):   # check for error here and try to reopen connection
                x = gps.readline()
                try:
                    msg = pynmea2.parse(x.decode("ISO-8859-1"))
                except pynmea2.nmea.ParseError as e:
                    print('-------------------------------------')
                    print(x.decode('ISO-8859-1'))
                    print("pynmea2.nmea.ParseError: {}".format(e))
                    print('-------------------------------------')

                if((msg.talker=='GN' and msg.sentence_type=='RMC') and msg.status=='A'):
                   #print(x.decode('ISO-8859-1').strip())
                   last_seen_rmc = msg.timestamp
                   gps_tuple = time.struct_time((msg.datestamp.year, \
                                            msg.datestamp.month, \
                                            msg.datestamp.day, \
                                            msg.timestamp.hour, \
                                            msg.timestamp.minute, \
                                            msg.timestamp.second, \
                                            -1, -1, 0 ))
                   current['gps_time'] = timegm(gps_tuple)

                   # convert goofy GPS DDmm.mm to decimal degrees
                   DD = int(float(msg.lat)/100)
                   mm = float(msg.lat)-DD*100
                   DDmm = DD+mm/60
                   if(msg.lat_dir == 'S'):
                      current['lat'] = -DDmm
                   else:
                      current['lat'] = DDmm
                   DD = int(float(msg.lon)/100)
                   mm = float(msg.lon)-DD*100
                   DDmm = DD+mm/60
                   if(msg.lon_dir == 'W'):
                      current['lon'] = -DDmm
                   else:
                      current['lon'] = DDmm
                   current['spd_kts'] = msg.spd_over_grnd  # knots
                   current['course'] = msg.true_course      # only valid when moving 
                   next

                if((msg.talker=='GN' and msg.sentence_type=='GGA') and msg.gps_qual>0 ):
                   #print(x.decode('ISO-8859-1').strip())
                   #print("altitude: {}, geo_sep: {}, sum: {:.1f}".format(float(msg.altitude),float(msg.geo_sep),(float(msg.altitude)+float(msg.geo_sep))))
                   #print(repr(msg))
                   last_seen_gga = msg.timestamp
                   if(msg.altitude_units=='M'):
                      current['alt_msl'] = msg.altitude
                   if(msg.geo_sep_units=='M'):
                      current['geo_sep'] = msg.geo_sep
                   # convert goofy GPS DDmm.mm to decimal degrees
                   DD = int(float(msg.lat)/100)
                   mm = float(msg.lat)-DD*100
                   DDmm = DD+mm/60
                   if(msg.lat_dir == 'S'):
                      current['lat'] = -DDmm
                   else:
                      current['lat'] = DDmm
                   DD = int(float(msg.lon)/100)
                   mm = float(msg.lon)-DD*100
                   DDmm = DD+mm/60
                   if(msg.lon_dir == 'W'):
                      current['lon'] = -DDmm
                   else:
                      current['lon'] = DDmm
                   next

                if((msg.talker=='PC' and msg.sentence_type=='LMP') and msg.gps_qual>0 ):
                    last_seen_pclmp = msg.timestamp
                    roll = float(msg.data[1])
                    pitch = float(msg.data[2])
                    mag_heading = float(msg.data[3])
                    print("Mag heading: {:.2f} Roll: {:.2f} Pitch: {.2f}".format(mag_heading, roll, pitch))

            else:
               time.sleep(0.1)

            if ((last_seen_gga == last_seen_rmc)): # and (last_seen_gga == last_seen_pclmp)):
               #print("Got a complete set!  let's submit a MQTT message.")
               current['time']=int(time.time()*10)/10
               if(current['alt_msl'] == -999.0):
                  current['declination'] = int(geomag.declination(current['lat'],current['lon']))
               else:
                  current['declination'] = geomag.declination(current['lat'],current['lon'],current['alt_msl'])
               if(current['mag_heading']>-999.0 and current['declination']>-999.0):
                  current['true_heading'] = current['mag_heading'] + current['declination']
               current['true_heading'] = int(current['true_heading']*100)/100
               current['declination'] = int(current['declination']*100)/100
               try:
                  mqttString = 'gps/{} {}'.format(WXT_SERIAL, json.dumps(current))
                  print("MQTT pub: {}".format(mqttString))
                  client.publish('gps/{}'.format(WXT_SERIAL), json.dumps(current))
               except:
                  print("MQTT pub: failure")

               # reset last seen messages, prepare for new pair
               last_seen_rmc = datetime.time(0,0,2)
               last_seen_gga = datetime.time(0,0,1)
               last_seen_pclmp = datetime.time(0,0,3)
               current = missing_values



if (__name__ == '__main__'):
    main()

