#!/usr/bin/env python3
"""
    GPS location for dragino module - sends GPS sourced latitude, longitude & altitude out over LoRaWAN 50 times with 5 minutes intervals using CayenneLPP  
    and FUTURE option to adhere to a 1% duty cycle

    Note - observations are packets arrving at TTN are often concattonated - to be investigated. Results still seem to work and be correct. More testing required. - See TTNMapper alternative
    Installation uses - 
    wget https://github.com/FEEprojects/cayennelpp-python/releases/download/v1.0.0/simplecayennelpp-1.0.0.tar.gz
    #install it
    sudo pip3 install simplecayennelpp-1.0.0.tar.gz
    Options to use other Cayenne LPP to be investigated

    cache.json will be created if it doesn't exist
"""
import logging
from datetime import datetime
from time import sleep
import RPi.GPIO as GPIO
from dragino import Dragino
from dragino.GPShandler import GPS
from simplecayennelpp import CayenneLPP # import the module required to pack th -
import binascii

GPIO.setwarnings(False)

gps=GPS()

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

while gps.lat is None:
   sleep(1)
lpp = CayenneLPP()

for i in range(0, 50):
    lpp.addGPS( 1, gps.lat, gps.lon, gps.alt)
    text=binascii.hexlify(lpp.getBuffer()).decode()
    sent=list(binascii.unhexlify(text))
    D.send_bytes(sent)
    print(text)
    #print(sent)
    print(gps.lat, gps.lon, gps.alt)
    sleep(5)
    start = datetime.utcnow()
    while D.transmitting:
        pass
    end = datetime.utcnow()
    print("Sent GPS Co-Ordinates (LPP) message ({})".format(end-start))
    print(sent)
    sleep(295)
#    sleep(99*D.lastAirTime()) # limit to 1% duty cycle
