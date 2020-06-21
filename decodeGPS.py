#!/usr/bin/python3

# altitude is sum of geoidal seperation and ellipsoid altitude (ie. GPGGA provides an estimate of MSL as well as the undulation)
# https://gis.stackexchange.com/questions/174046/relation-between-geoidal-separation-and-antenna-altitude-in-gga-sentence

# read sentences from GPS (multi-sensor unit), decode, and publish to MQTT as JSON strings
#  /gps/SERIAL_NUMBER  (match serial to WXT unit in use)
# calculate true heading using GPS location and magnetic heading

import sys
import time
import logging
import datetime
from calendar import timegm
import json
import serial
import pynmea2
import geomag
import geoidheight.geoid
import numpy as np
import paho.mqtt.client as mqtt
from secret import *

LOCAL_BROKER_ADDRESS = '127.0.0.1'  # MQTT broker address
REMOTE_BROKER_ADDRESS = 'kennedy.tw'  # remote MQTT broker address
WXT_SERIAL = 'N3720229' # PTU S/N N3620062
WXT_ELEVATION = 375.0   # WXT sensor elevation in meters above MSL
GPS_SERIAL_DEVICE = '/dev/ttyACM0'
GPS_BAUDRATE = 19200

missing_values = {
   'time': None,         # time from pc clock, expressed as seconds since the Unix epoch (01-01-1970)
   'gps_time': None,     # time from gps, expressed as seconds since Unix epoch (01-01-1970)
   'lat': None,          # latitude in decimal degrees, positive values are N
   'lon': None,          # longitude in decimal degrees, positive values are W
   'course': None,       # course over ground in degrees
   'spd_kts': None,      # speed over ground in knots
   'alt_msl': None,      # altitude above MSL (negative below MSL), meters
   'geo_sep': None,      # distance between WGS84 ellipsoid and GPS receiver geoid, meters
   'geo_sep_egm2008': None, # distance between WGS84 ellipsoid and egm2008-1 geoid, meters
   'alt_wgs84': None,     # altitude above wgs84 ellipsoid, meters
   'alt_egm2008': None,   # altitude above egm2008-1 geoid (approx sea level), meters
   'internal_pres': None, # pressure from arduino sensor (BMP85)
   'internal_temp': None, # temperature from arduino sensor (BMP85) usually higher than room temp
   'roll': None,         # roll angle in degrees
   'pitch': None,        # pitch angle in degrees
   'mag_heading': None,  # magnetic compass heading in degrees
   'true_heading': None, # true heading, sum of mag_heading and declination
   'declination': None,  # computed using geomag delination function, WMM2020 model using GPS (lat/lon/alt)
}

# function to convert string to float.  returns 'None' if the float conversion fails
def safe_float(string):
    try:
        return(float(string))
    except:
        return(None)

# function to convert string to int.  returns 'None' if the int conversion fails
def safe_int(string):
    try:
        return(int(string))
    except:
        return(None)

def isfloat(value):
  try:
    float(value)
    return True
  except ValueError:
    return False

# now we define the callbacks to handle messages we subcribed to
def on_message(client, userdata, message):
    global gps
    print("message received: {0}".format(str(message.payload.decode("ISO-8859-1"))))
    print("message topic: {0}".format(message.topic))
    print("message qos: {0}".format(message.qos))
    print("message retain flag: {0}".format(message.retain))
    command = message.payload.decode('ISO-8859-1')
    logging.info('MQTT sub: {}: {}'.format(message.topic, command))
    command += '\r\n'
    try:
        gps.send(command.encode('ISO-8859-1'))
    except:
        logging.warning("MQTT command send to GPS failed".format(time.asctime()))

def main():
        global gps
        global geoidheight

        geoidheight = geoidheight.geoid.GeoidHeight()
        last_seen_rmc = None
        last_seen_gga = None
        last_seen_pclmp = None
        current = missing_values  # we fill these in as we receive sentences

        FORMAT = '%(asctime)s %(levelname)s: %(message)s'
        logging.basicConfig(level=logging.DEBUG, format=FORMAT, datefmt='%m/%d/%Y %H:%M:%S')
        logging.info("starting decodeGPS.py")

        client = mqtt.Client('gps-{}-cmd'.format(WXT_SERIAL))
        client.on_message = on_message
        client.username_pw_set(MQTT_USERNAME,MQTT_PASSWORD);
        client.connect(LOCAL_BROKER_ADDRESS)
        client.loop_start()
        client.subscribe('gps/{}/cmd'.format(WXT_SERIAL))  # subscribe to command channel

        while True:
            try:
                gps = serial.Serial(GPS_SERIAL_DEVICE, GPS_BAUDRATE, timeout=1.0)  # open arduino combo device
                break
            except (serial.serialutil.SerialException,PermissionError) as e:
                logging.critical("can't initialize serial device for GPS, {}".format(e))
                time.sleep(5)

        while True:
            if (gps.in_waiting):   # check for error here and try to reopen connection
                x = gps.readline()
                #logging.debug(x.decode('ISO-8859-1').strip())
                try:
                    msg = pynmea2.parse(x.decode("ISO-8859-1"))
                except pynmea2.nmea.ParseError as e:
                    logging.debug("pynmea2.nmea.ParseError: {}".format(e))
                    #logging.debug(x.decode('ISO-8859-1').strip())
                    continue  # gps string malformed, skip and read the next one

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
                   try:
                       current['gps_time'] = timegm(gps_tuple)
                   except ValueError as e:
                       logging.warning("Invalid time found in GNRMC sentence {}".format(e))
                       logging.info(x.decode('ISO-8859-1').strip())

                   try:
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
                       # check bounds on lat/lon
                       if((current['lat']>90.0) or (current['lat']<-90.0)):
                          current['lat'] = None
                       if((current['lon']>180.0) or (current['lon']<-180.0)):
                          current['lon'] = None
                   except ValueError as e:
                       logging.info("Invalid lat/lon found in GNRMC sentence {}".format(e))
                       logging.info(x.decode('ISO-8859-1').strip())

                   current['spd_kts'] = msg.spd_over_grnd   # knots
                   current['course'] = msg.true_course      # only valid when moving 
    
                if((msg.talker=='GN' and msg.sentence_type=='GGA') and msg.gps_qual>0 ):
                   #print(x.decode('ISO-8859-1').strip())
                   #print("altitude: {}, geo_sep: {}, sum: {:.1f}".format(float(msg.altitude),float(msg.geo_sep),(float(msg.altitude)+float(msg.geo_sep))))
                   #print(repr(msg))
                   last_seen_gga = msg.timestamp
                   if(msg.altitude_units=='M'):
                       current['alt_msl'] = msg.altitude
                   if(msg.geo_sep_units=='M'):
                       current['geo_sep'] = safe_float(msg.geo_sep)

                   try:
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
                       # check bounds on lat/lon
                       if((current['lat']>90.0) or (current['lat']<-90.0)):
                          current['lat'] = None
                       if((current['lon']>180.0) or (current['lon']<-180.0)):
                          current['lon'] = None
                   except ValueError as e:
                       logging.info("Invalid lat/lon found in GNRMC sentence {}".format(e))
                       logging.info(x.decode('ISO-8859-1').strip())
 
                if((msg.talker=='PC' and msg.sentence_type=='LMP') and msg.gps_qual>0 ):
                    last_seen_pclmp = msg.timestamp
                    current['roll'] = safe_float(msg.data[1])
                    current['pitch'] = safe_float(msg.data[2])
                    current['mag_heading'] = safe_float(msg.data[3])
                    logging.debug("Mag heading: {:.2f} Roll: {:.2f} Pitch: {.2f}".format(mag_heading, roll, pitch))


            else:
               time.sleep(0.1)  # on serial data available

            if ((last_seen_gga == last_seen_rmc) and last_seen_gga is not None):   # and (last_seen_gga == last_seen_pclmp)):
               #print("Got a complete set!  let's submit a MQTT message.")
               current['time']=round(time.time(),2)  # unix epoch time to 2 places  
               if(current['lat'] is not None and current['lon'] is not None):
                   if(current['alt_msl'] is None):
                       current['declination'] = geomag.declination(current['lat'],current['lon'])
                   else:
                       current['declination'] = geomag.declination(current['lat'],current['lon'],current['alt_msl'])
                   current['declination'] = round(current['declination'],2)
               else:
                   current['declination'] = None

               if(current['mag_heading'] is not None and current['declination'] is not None):
                   current['true_heading'] = current['mag_heading'] + current['declination']
                   current['true_heading'] = round(current['true_heading'],2)

               #calculate geoid height from model
               if (current['lat'] is not None and current['lon'] is not None):
                   current['geo_sep_egm2008'] = geoidheight.get(float(current['lat']),float(current['lon']))
                   current['alt_wgs84'] = current['alt_msl']+current['geo_sep']
                   current['alt_egm2008'] = current['alt_wgs84']-current['geo_sep_egm2008']
               else:
                   current['geo_sep_egm2008'] = None
                   current['alt_wgs84'] = None
                   current['alt_egm2008'] = None
               
               # publish the gps JSON 
               try:
                   mqttString = 'gps/{} {}'.format(WXT_SERIAL, json.dumps(current))
                   #logging.info('MQTT publish')
                   logging.debug('MQTT pub: {}'.format(mqttString))
                   client.publish('gps/{}'.format(WXT_SERIAL), json.dumps(current))
               except:
                   logging.warning("MQTT pub: failure {}".format(mqttString))

               # reset last seen messages, prepare for new pair
               last_seen_rmc = None
               last_seen_gga = None
               last_seen_pclmp = None
               current = missing_values



if (__name__ == '__main__'):
    while True:
        try:
            main()
        except Exception as e:
            logging.critical("unhandled exception in decodeGPS.py, {}".format(e))
            #raise
            time.sleep(5)

