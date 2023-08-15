#!/usr/bin/env python3
"""
    Test harness for dragino module - sends hello world out over LoRaWAN 5 times
    and adheres to a 1% duty cycle

    cache.json will be created if it doesn't exist
"""
import logging
from time import sleep
import RPi.GPIO as GPIO
from dragino import Dragino

GPIO.setwarnings(False)

# add logfile but make sure it starts empty for this run
f=open("test.log","w")
f.close()
logLevel=logging.DEBUG
logging.basicConfig(filename="test.log", format='%(asctime)s - %(funcName)s - %(lineno)d - %(levelname)s - %(message)s', level=logLevel)

# create a Dragino object and join to TTN
D = Dragino("dragino.toml", logging_level=logLevel)
D.join()

print("Waiting for JOIN ACCEPT")
while not D.registered():
    print(".",end="")
    sleep(2)
print("\nJoined")

for i in range(0, 5):
    D.send("Hello World")
    print("Sent Hello World message")
    while D.transmitting:
        sleep(0.1)
    sleep(99*D.lastAirTime()) # limit to 1% duty cycle
