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
#define SENSOR_MAG_OFFSET_X 11.955
#define SENSOR_MAG_OFFSET_Y 12.135
#define SENSOR_MAG_OFFSET_Z 0
#define SENSOR_ACCEL_OFFSET_X -0.40
#define SENSOR_ACCEL_OFFSET_Y -0.18
#define SENSOR_ACCEL_OFFSET_Z 0.41
#define SAMPLES 600

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

#define PMTK_SET_NMEA_UPDATE_0_2HZ  "$PMTK220,5000*1B"
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
  delay(250);
  Serial.println(F("Multi-sensor logger v1.1")); Serial.println("");
  
  /* Initialise the sensors */
  initSensors();
  delay(250);
  mySerial.println(PMTK_SET_NMEA_OUTPUT_RMCGGA);  // set RMC and GGA output
  delay(250);
  mySerial.println(PMTK_SET_NMEA_UPDATE_0_2HZ);     // set GPS data rate
  delay(250);
  while (mySerial.available()) {                  // flush GPS serial port input buffer
    mySerial.read();
  }
}

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
  float heading;
  float mag_x, mag_y, mag_z;
  float accel_x, accel_y, accel_z;
  char c;

  // trigger on incoming GPS sentence
  while(!mySerial.available()) {
    delay(1);
  }

  // read/print GPS stings until pause after end of line character
  //  i.e. \n newline received, and no characters immediately available.
  //  there is much jitter in GPS output timing. 
  //   so keep copying characters until a newline is seen, and continue
  //   to wait for sentences for at least  XXXX msec or so.
  //   XXXX depends on frequency of GPS output.
  
  long gpsTimeout = millis();
  if(mySerial.available()) {
    do {
      while(mySerial.available()) {
        c = mySerial.read();
        Serial.print(c);
      }
    } while ((c != '\n') || ((millis() - gpsTimeout) < 1000));
    if (c != '\n') {
      Serial.print('\n');
    }
  }

   mag_x = 0;
   mag_y = 0;
   mag_z = 0;

   accel_x = 0;
   accel_y = 0;
   accel_z = 0;
   
    for (int counter=0; counter <SAMPLES; counter++) {
     while (!mag.getEvent(&mag_event)) {
        //Serial.println("Failure in magnetometer");
     }
     while (!accel.getEvent(&accel_event)) {
       //Serial.println("Failure in accelerometer");
     }
  
  
     mag_x += mag_event.magnetic.x;
     mag_y += mag_event.magnetic.y;
     mag_z += mag_event.magnetic.z;
     
     accel_x += accel_event.acceleration.x;
     accel_y += accel_event.acceleration.y;
     accel_z += accel_event.acceleration.z;
  }

  mag_x = mag_x/SAMPLES;
  mag_y = mag_y/SAMPLES;
  mag_z = mag_z/SAMPLES;

  accel_x = accel_x/SAMPLES;
  accel_y = accel_y/SAMPLES;
  accel_z = accel_z/SAMPLES;

  // apply 2D correction for hard iron offsets
  mag_x -= SENSOR_MAG_OFFSET_X;
  mag_y -= SENSOR_MAG_OFFSET_Y;
  mag_z -= SENSOR_MAG_OFFSET_Z;
  mag_z /= 2;  // output of z axis is double

  // apply accelerometer offsets
  accel_x -= SENSOR_ACCEL_OFFSET_X; 
  accel_y -= SENSOR_ACCEL_OFFSET_Y; 
  accel_z -= SENSOR_ACCEL_OFFSET_Z; 

   while(!bmp.getEvent(&bmp_event)) {
    
  }
  bmp.getTemperature(&temperature);

  heading = 180 + 57.2957795131 * atan2(mag_y, mag_x);



  // Use this code for calibration
/*  Serial.print(F("Mag X: "));  // 9:55    46    32
  Serial.print(mag_event.magnetic.x);
  Serial.print(F(" Y: "));  // -17  : 28    45   22.5-17  5.5
  Serial.print(mag_event.magnetic.y);
  Serial.print(F(" Z: "));
  Serial.print(mag_event.magnetic.z);  // -15 : 87    102  87-51=36
  Serial.println("");
  Serial.print(F("Accel X: "));
  Serial.print(accel_event.acceleration.x);
  Serial.print(F(" Y: "));
  Serial.print(accel_event.acceleration.y);
  Serial.print(F(" Z: "));
  Serial.print(accel_event.acceleration.z);
  Serial.println("");
  */


  // compute pitch/roll from accelerometer readings
  dof.accelGetOrientation(&accel_event, &orientation);

  // compute heading from mag sensor readings
  //dof.magGetOrientation(SENSOR_AXIS_Z, &mag_event, &orientation);

  strcpy (gpsMessage, "$PCLMP2,");  // initialize the string
  dtostrf(orientation.roll, 0, 2, buffer);
  strcat (gpsMessage, buffer);
  strcat (gpsMessage, ",");
  dtostrf(orientation.pitch, 0, 2, buffer);
  strcat (gpsMessage, buffer);
  strcat (gpsMessage, ",");
  //dtostrf(orientation.heading, 0, 2, buffer);
  dtostrf(heading, 0, 2, buffer);
  strcat (gpsMessage, buffer);
  strcat (gpsMessage, ",");
  dtostrf(bmp_event.pressure, 0, 2, buffer);
  strcat (gpsMessage, buffer);
  strcat (gpsMessage, ",");
  dtostrf(temperature, 0, 2, buffer);
  strcat (gpsMessage, buffer);
  strcat (gpsMessage, "*");

  gpsChecksum(gpsMessage);

  //strcat (gpsMessage, "\r\n");

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

  Serial.print(gpsMessage);    
  Serial.println(F(""));
 
  
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
