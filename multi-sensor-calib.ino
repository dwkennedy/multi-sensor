/*  $PCMLP2,ROLL,PITCH,MAG_HEADING,TEMP,PRESSURE*chk
*/

#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_LSM303_U.h>
#include <Adafruit_BMP085_U.h>
#include <Adafruit_L3GD20_U.h>
#include <Adafruit_10DOF.h>
#include <Adafruit_GPS.h>
#include <SoftwareSerial.h>

// mag sensor 2D correction values
//#define SENSOR_MAG_OFFSET_X 33.3265
//#define SENSOR_MAG_OFFSET_Y 2.93956
//#define SENSOR_MAG_OFFSET_X 32.6935
//#define SENSOR_MAG_OFFSET_Y 5.43078
//#define SENSOR_MAG_OFFSET_Z 36

#define SAMPLES 100
#define SENSOR_MAG_OFFSET_X 31.0174
#define SENSOR_MAG_OFFSET_Y 6.06801
#define SENSOR_MAG_OFFSET_Z 36
#define SENSOR_ACCEL_OFFSET_X 0.0
#define SENSOR_ACCEL_OFFSET_Y 0.045
#define SENSOR_ACCEL_OFFSET_Z 0.41

/* Assign a unique ID to the sensors */
Adafruit_10DOF                dof   = Adafruit_10DOF();
Adafruit_LSM303_Accel_Unified accel = Adafruit_LSM303_Accel_Unified(30301);
Adafruit_LSM303_Mag_Unified   mag   = Adafruit_LSM303_Mag_Unified(30302);
Adafruit_BMP085_Unified       bmp   = Adafruit_BMP085_Unified(18001);

/* Update this with the correct SLP for accurate altitude measurements */
float seaLevelPressure = SENSORS_PRESSURE_SEALEVELHPA;

SoftwareSerial mySerial(8, 7);
static const char hex[] = "0123456789ABCDEF";
char gpsMessage[92];
char buffer[12];


#define PMTK_SET_NMEA_UPDATE_1HZ  "$PMTK220,1000*1F"
#define PMTK_SET_NMEA_UPDATE_5HZ  "$PMTK220,200*2C"
#define PMTK_SET_NMEA_UPDATE_10HZ "$PMTK220,100*2F"

// turn on only the second sentence (GPRMC)
#define PMTK_SET_NMEA_OUTPUT_RMCONLY "$PMTK314,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0*29"
// turn on GPRMC and GGA
#define PMTK_SET_NMEA_OUTPUT_RMCGGA "$PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0*28"
// turn on ALL THE DATA
#define PMTK_SET_NMEA_OUTPUT_ALLDATA "$PMTK314,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0*28"
// turn off output
#define PMTK_SET_NMEA_OUTPUT_OFF "$PMTK314,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0*28"

#define PMTK_Q_RELEASE "$PMTK605*31"


/**************************************************************************/
/*!
    @brief  Initialises all the sensors used by this example
*/
/**************************************************************************/
void initSensors()
{
  if(!accel.begin())
  {
    /* There was a problem detecting the LSM303 ... check your connections */
    Serial.println(F("Ooops, no LSM303 detected ... Check your wiring!"));
    while(1);
  }
  if(!mag.begin())
  {
    /* There was a problem detecting the LSM303 ... check your connections */
    Serial.println("Ooops, no LSM303 detected ... Check your wiring!");
    while(1);
  }
  if(!bmp.begin())
  {
    /* There was a problem detecting the BMP180 ... check your connections */
    Serial.println("Ooops, no BMP180 detected ... Check your wiring!");
    while(1);
  }
}

/**************************************************************************/
/*!

*/
/**************************************************************************/
void setup(void)
{
  while (!Serial); // wait for leonardo to be ready
  
  Serial.begin(115200);  // phony baud rate for USB
  mySerial.begin(9600);  // GPS baud rate
  delay(1000);
  Serial.println(F("Multi-sensor logger calibration v1.0")); Serial.println("");
  
  /* Initialise the sensors */
  initSensors();
  mySerial.println(PMTK_SET_NMEA_OUTPUT_RMCGGA);  // set RMC and GGA output
  mySerial.println(PMTK_SET_NMEA_UPDATE_1HZ);     // set GPS data rate
  while (mySerial.available()) {                  // flush GPS serial port input buffer
    mySerial.read();
  }
}

long counter = 0;
float mag_x = 0;
float mag_y = 0;
float mag_z = 0;
float accel_x = 0;
float accel_y = 0;
float accel_z = 0;


/**************************************************************************/
/*!
    @brief  Constantly check the roll/pitch/heading/altitude/temperature
*/
/**************************************************************************/
void loop(void)
{
  sensors_event_t accel_event;
  sensors_event_t mag_event;
  sensors_event_t bmp_event;
  sensors_vec_t   orientation;

  float temperature;

  accel.getEvent(&accel_event);
  mag.getEvent(&mag_event);
  bmp.getEvent(&bmp_event);
  bmp.getTemperature(&temperature);

  // apply 2D correction for hard iron offsets
  /*mag_event.magnetic.x -= SENSOR_MAG_OFFSET_X;
  mag_event.magnetic.y -= SENSOR_MAG_OFFSET_Y;
  mag_event.magnetic.z -= SENSOR_MAG_OFFSET_Z;
  mag_event.magnetic.z /= 2;  // output of z axis is double

  // apply accelerometer offsets
  accel_event.acceleration.x -= SENSOR_ACCEL_OFFSET_X; 
  accel_event.acceleration.y -= SENSOR_ACCEL_OFFSET_Y; 
  accel_event.acceleration.z -= SENSOR_ACCEL_OFFSET_Z; 
  */

  mag_x += mag_event.magnetic.x;
  mag_y += mag_event.magnetic.y;
  mag_z += mag_event.magnetic.z;
  accel_x += accel_event.acceleration.x;
  accel_y += accel_event.acceleration.y;
  accel_z += accel_event.acceleration.z;
  
  // Use this code for calibration
  if (counter++ >= SAMPLES) {
    Serial.print(F("Mag X: "));  // 9:55    46    32
    Serial.print(mag_x/SAMPLES);
    Serial.print(F(" Y: "));  // -17  : 28    45   22.5-17  5.5
    Serial.print(mag_y/SAMPLES);
    Serial.print(F(" Z: "));
    Serial.print(mag_z/SAMPLES);
    Serial.println("");
    Serial.print(F("Accel X: "));
    Serial.print(accel_x/SAMPLES);
    Serial.print(F(" Y: "));
    Serial.print(accel_y/SAMPLES);
    Serial.print(F(" Z: "));
    Serial.print(accel_z/SAMPLES);
    Serial.println("");


/*
  // compute pitch/roll from accelerometer readings
  dof.accelGetOrientation(&accel_event, &orientation);

  // compute heading from mag sensor readings
  dof.magGetOrientation(SENSOR_AXIS_Z, &mag_event, &orientation);

  strcpy (gpsMessage, "$PCLMP2,");  // initialize the string
  dtostrf(orientation.roll, 0, 2, buffer);
  strcat (gpsMessage, buffer);
  strcat (gpsMessage, ",");
  dtostrf(orientation.pitch, 0, 2, buffer);
  strcat (gpsMessage, buffer);
  strcat (gpsMessage, ",");
  dtostrf(orientation.heading, 0, 2, buffer);
  strcat (gpsMessage, buffer);
  strcat (gpsMessage, ",");
  dtostrf(bmp_event.pressure, 0, 2, buffer);
  strcat (gpsMessage, buffer);
  strcat (gpsMessage, ",");
  dtostrf(temperature, 0, 2, buffer);
  strcat (gpsMessage, buffer);
  strcat (gpsMessage, "*");

  gpsChecksum(gpsMessage);

  strcat (gpsMessage, "\r\n");

/*  Serial.print(F("$PCLMP2,"));
  Serial.print(orientation.roll);
  Serial.print(F(","));
  Serial.print(orientation.pitch);
  Serial.print(F(","));
  Serial.print(orientation.heading);
  Serial.print(F(","));
  Serial.print(bmp_event.pressure);
  Serial.print(F(","));
  Serial.print(temperature);
  Serial.print(F("*XX"));
*/
    counter = 0;
    mag_x = 0; mag_y = 0; mag_z = 0;
    accel_x = 0; accel_y = 0; accel_z = 0;
    delay(1);
  }
}



boolean gpsChecksum(char *gpsMessage) {
  int8_t max = 90; // NMEA says 82, but there could have longer proprietary messages
  if (*gpsMessage != '$') return false;
  byte v = 0;
  for(;;) {
    if (--max <= 0) return false; // Protect from run away if no *
    byte b = *++gpsMessage;
    if (b == '*') break;
    v ^= b;
  }
  
  //unsigned char digit0 = hex[(v & 0xf0) >> 4];
  //unsigned char digit1 = hex[(v & 0x0f)];
  //if (gpsMessage[1] != digit0 || gpsMessage[2] != digit1) return false;
  //return true;

  gpsMessage[1] = hex[(v & 0xf0) >> 4];
  gpsMessage[2] = hex[(v & 0x0f)];
  gpsMessage[3] = 0;
  return true;
}
