#!/usr/bin/env python3
"""

	WARNING: don't forget to activate your virtual env before running

    TTN Test for dragino module - sends a short message  out over LoRaWAN N times
    and adheres to a 1% duty cycle. Stops sending when the Fair Use Limit is reached.
	
    cache.json will be created, if it doesn't exist, and will force a JOIN_REQUEST. 
	Cache.json will then contain the cached DevAddr and any other changes as a result of MAC command
	downlinks sent by the TTN server.
	
	To force a rejoin anytime delete cache.json before running this program.
	
	NOTE, in use this code stops sending after 171 transmissions, when the FUP has been reached.
	
	Changing the base_msg will reduce the number of transmissions.
	
	
	
	
"""
import logging
from time import sleep
from dragino import Dragino

# we are sending a msg and count
# e.g. "A 1" "A 2" etc
base_msg="A"


# set the max number of transmissions and the log file
# NOTE TTN Fair Use Policy of 30s TX in 24 hours may mean
# less messages are sent because the messages get longer
N=1000
LOG="testTTN.log"

# clear out the old log
with open(LOG,"w") as f:
    pass


# add logfile
logLevel=logging.DEBUG
logging.basicConfig(filename=LOG, format='%(asctime)s - %(funcName)s - %(lineno)d - %(levelname)s - %(message)s', level=logLevel)

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

print("\nJoined TTN")

TotalAirTime=0 # keep track to keep within TTN FUP

#

try:
    for i in range(0, N):
        msg=f"{base_msg} {i}"
        D.send(msg)
        print(f"Sent message {msg} ")
        while D.transmitting:
            sleep(0.1)
        airTime=D.lastAirTime()
        print(f"airTime={airTime}")
        TotalAirTime+=airTime
        if TotalAirTime>30:
            print("Reached fair use limit")
            exit(0)
        sleep(99*airTime) # limit to 1% duty cycle in EU

except Exception as e:
    print(f"Terminated by: {e}")

exit(0)
