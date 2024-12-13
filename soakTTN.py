#!/usr/bin/env python3
"""
    Test for dragino module - sends hello world out over LoRaWAN N times
    and adheres to a 1% duty cycle

    cache.json will be created if it doesn't exist
"""
import logging
from time import sleep
from dragino import Dragino

msg="A"
LOG="testTTN.log"


# add logfile
logLevel=logging.WARNING
logging.basicConfig(filename=LOG, filemode="w", format='%(asctime)s - %(funcName)s - %(lineno)d - %(levelname)s - %(message)s', level=logLevel)

# disbale verbose rports from ipython system
logging.getLogger('parso.cache').disabled=True
logging.getLogger('parso.cache.pickle').disabled=True

# create a Dragino object and join to TTN
D = Dragino("dragino.toml", logging_level=logLevel)
D.join()

print("Waiting for JOIN ACCEPT")
while not D.registered():
    print(".",end="")
    sleep(2)
print("\nJoined")


# calculate how many transmissions we can
# make per 24 hours
# FUP limits us to 30s per 24h
D.send(msg)
sleep(10)
airTime=D.lastAirTime()
while airTime==0:
    D.send(msg)
    sleep(10)
    airTime=D.lastAirTime()

    
    
numTxPer30s=30/airTime
interval=24*60*60/numTxPer30s - airTime # time between transmissions

print(f"tx time {airTime}s interval {interval}")

count=0
while True:
    try:
        print("count=",count)
        count+=1
        D.send(msg)
        sleep(interval)
    except Exception as e:
        print(f"Exception {e}")
        break