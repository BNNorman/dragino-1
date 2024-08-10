#!/usr/bin/env python3
"""
	WARNING: Don't forget to activate your virtual env before running this.
	
    Test for GPS module only.
	
	When first run the code waits till it receives a valid GPS message then 
	prints 10 readings at 5s intervals
	
	NOTE: The GPSHandler runs the GPS updater in a seperate thread
	
"""
import logging
from time import sleep
from dragino import Dragino

LOG="GPS.log"


# add logfile
logLevel=logging.DEBUG
logging.basicConfig(filename=LOG, format='%(asctime)s - %(funcName)s - %(lineno)d - %(levelname)s - %(message)s', level=logLevel)

# disbale verbose rports from ipython system
logging.getLogger('parso.cache').disabled=True
logging.getLogger('parso.cache.pickle').disabled=True

# create a Dragino object. Do not join to TTN (not needed)
D = Dragino("dragino.toml", logging_level=logLevel,enableGPS=True)

# it may take some time for GPS to lock onto the satellites
# often this can be as long as a minute BUT and active antenna
# tends to speed that up.
while D.get_gps()==(None,None,None,None):
    print("Waiting for GPS data")
    sleep(1)

# display 10 readings one every 5s - you should see the timestamp changing
for i in range(10):
    print(D.get_gps())
	sleep(5)
	
	
print("GPS test Finished")
