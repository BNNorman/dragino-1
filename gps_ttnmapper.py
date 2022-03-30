#!/usr/bin/env python3
"""
    GPS location for dragino module - sends GPS sourced latitude, longitude, altitude & hdop out over LoRaWAN 50 times with 5 minute intervals  
    and FUTURE to potentially adhere to a 1% duty cycle

    cache.json will be created if it doesn't exist
"""
import logging
from datetime import datetime
from time import sleep
import RPi.GPIO as GPIO
from dragino import Dragino
from dragino.GPShandler import GPS

GPIO.setwarnings(False)

gps=GPS()

def convert_payload(lat, lon, alt, hdop):
    """
        Converts to the format used by ttnmapper.org - See webhook v3 intergration and use the included or reference javascript decoder
        https://github.com/ttn-be/gps-node-examples/blob/master/Sodaq/sodaq-one-ttnmapper/decoder.js

    """

    payload = []
    latb = int(((lat + 90) / 180) * 0xFFFFFF)
    lonb = int(((lon + 180) / 360) * 0xFFFFFF)
    altb = int(round(float(alt), 0))
    hdopb = int(float(hdop) * 10)

    payload.append(((latb >> 16) & 0xFF))
    payload.append(((latb >> 8) & 0xFF))
    payload.append((latb & 0xFF))
    payload.append(((lonb >> 16) & 0xFF))
    payload.append(((lonb >> 8) & 0xFF))
    payload.append((lonb & 0xFF))
    payload.append(((altb  >> 8) & 0xFF))
    payload.append((altb & 0xFF))
    payload.append(hdopb & 0xFF)
    return payload

# add logfile
#logLevel=logging.DEBUG
logLevel=logging.INFO
#logging.basicConfig(filename="gps.log", format='%(asctime)s - %(funcName)s - %(lineno)d - %(levelname)s - %(message)s', level=logLevel)

# create a Dragino object and join to TTN
D = Dragino("dragino.toml", logging_level=logLevel, enableGPS=True)
D.join()

print("Waiting for JOIN ACCEPT")
while not D.registered():
    print(".",end="")
    sleep(2)
print("\nJoined")

#while gps.lat is None:
while gps.hdop is None:
   print("Waiting for valid SKY [hdop - Horizontal Dilution of Precision] value",gps.lat, gps.lon, gps.alt, gps.hdop)
   sleep(1)

for i in range(0, 50):
    sent=convert_payload(gps.lat, gps.lon, gps.alt, gps.hdop)
    D.send_bytes(sent)
    print(sent)
    print(gps.lat, gps.lon, gps.alt, gps.hdop)
    sleep(5)
    start = datetime.utcnow()
    while D.transmitting:
        pass
    end = datetime.utcnow()
    print("Sent GPS Co-Ordinates (TTN Mapper) message ({})".format(end-start))
    sleep(295)
#    sleep(99*D.lastAirTime()) # limit to 1% duty cycle
