"""
GPShandler.py

Code to manage the Dragino GPS device

provides non-blocking access using GPSD

"""
import logging
from threading import Thread
from gps3 import agps3

import json
from time import time,sleep
from datetime import datetime,timedelta

DEFAULT_LOG_LEVEL=logging.INFO
VERBOSE=False #

class GPS:
    def __init__(self, logging_level=DEFAULT_LOG_LEVEL,threaded=True,threadDelay=0.5):

        self.logger = logging.getLogger("GPS")
        self.logger.setLevel(logging_level)
        logging.basicConfig(format='%(asctime)s - %(name)s - %(lineno)d - %(levelname)s - %(message)s')


        self.isThreaded=threaded
        self.threadLoopDelay=threadDelay

        self.lat=None
        self.lon=None
        self.alt=None
        self.hdop=None
        self.timestamp=None
        self.lastGpsReading=None

        # gpsd settings - make sure gpsd is installed and running
        try:
            self.gpsd_socket = agps3.GPSDSocket()
            self.data_stream = agps3.DataStream()
            self.gpsd_socket.connect() #'127.0.0.1', 2947) default
            self.gpsd_socket.watch(gpsd_protocol='json', enable=True)
            
        except Exception as e:
            self.logger.exception(f"Unable to setup GPSD {e}")


        if self.isThreaded:
            self.running=False
            self.stopped=True
            self.logger.info("starting GPS updater thread")
            self.gpsThread=Thread(target=self._updater)
  
            self.gpsThread.start()


        # sentences are cached here with a timestamp (for time correction)
        self.gps_cache={}

    def __del__(self):
        if self.isThreaded:
            self.logger.info("Stopping the background thread")
            self.running=False
            while not self.stopped:
                pass
            self.logger.info("GPS updater has stopped")

    def stop(self):
        self.__del__()
        
    def get_gps(self):
        """
            return the cached GPS values

            update_gps() should be called frequently to keep
            these values updated

        """
        self.logger.debug(f"get_gps(): lat {self.lat}, lon {self.lon}, alt {self.alt}, hdop {self.hdop}")
        return self.lat, self.lon, self.alt, self.hdop

    def get_corrected_timestamp(self):
        """
            return the timestamp for Now

            The system time may have drifted since the last valid GPS timestamp.

            The current timestamp will be the last GPS timestamp plus the elapsed time
            since the reading was obtained (usually within a few seconds if the GPS
            has achieved a lock)

        """

        return datetime.fromtimestamp(self.timestamp)+timedelta(time()-self.lastGpsReading)

    def delay(self,Delay):
        """
        delay which does not sleep the thread

        :Param Delay: float (seconds)
        """
        #sleep(Delay)
        start=time()
        while True:
            if (time()-start)>=Delay:
                break
            sleep(0.1)

    def getSentences(self):
        """
        Returns a list of cached sentences
        """
        return self.gpc_cache.keys()


    def getSentence(self,which):
        """
        getSentence

        Caller MUST know which sentence they want but it may not have been
        seen and cached when asked for.

        which:  String like 'TPV', 'SKY' etc case insensitive
        return: None or the requested GPS sentence (a dictionary)
        """
        which=which.toupper()
        if which in self.gps_cache:
            return self.gps_cache[which]
        return None

    def _updater(self):
        """
        GPS updater thread, samples GPS typically every 0.5 seconds
        """
        self.logger.debug("GPS updater starting ")
        self.running=True
        self.stopped=False
        while self.running:
            self.update_gps()
            self.delay(self.threadLoopDelay)
        self.logger.warn("GPS handler stopped")
        self.stopped=True
		
    def update_gps(self):
        """
            Get the GPS position from the dragino,
            using gpsd

            updates the cached GPS values when a TPV message is seen
            this could mean the cached time is out of sync with reality
            so we also save a timestamp when the reading was valid

            Caller can compute actual time using the GPS timestamp and the
            time the reading was cached.

        """
        try:
            if VERBOSE: 
                self.logger.debug("update GPS")
            new_data = self.gpsd_socket.next()
            
            if new_data is not None:
                data = json.loads(new_data)
                if VERBOSE:
                    self.logger.info("GPS new_data class %s", data["class"])

                # cache all GPS messages with a reading timestamp
                # the reading timestamp allows correction to GPS timestamp
                # since the sentence may have been seen some time before used
                data["lastReadingTime"]=time()
                self.gps_cache[data["class"]]=data

                # what follows will be deprecated
                if data["class"] == "TPV":
                #    print("TPV data",data)
                    if data["mode"]==0 or data["mode"]==1:
                        # no useable data or no fix
                        self.logger.info("No GPS fix (yet)")
                        return 
                        
                    try:
                        self.lat = data["lat"]
                        self.lon = data["lon"]
                        self.alt = data["alt"]
                        self.timestamp = data["time"]
                        #print(f"Got lat {self.lat} lon {self.lon} alt {self.alt} at {self.timestamp}") 
                        self.lastGpsReading = time()
                    except KeyError as e:
                        self.logger.exception(f"unable to extract TPV data missing key error: {e}")
                if data["class"] == "SKY":
                    #print("SKY data",data)
                    self.hdop = data["hdop"]
                    print(f"Got lat {self.lat} lon {self.lon} alt {self.alt} hdop {self.hdop} at {self.timestamp}") 
                else:
                    if VERBOSE:
                        self.logger.debug(f"GPS message was {data}")
                    pass
            else:
                if VERBOSE:
                    self.logger.debug("No new gps data")
                
        except Exception as e:
            self.logger.warning(f"ignoring exception {e}")


if __name__=="__main__":
    
    gps=GPS()


    nofix=True
    start=time()
    
    try:
        start=time()
        while True:

            TPV=gps.getSentence("TPV")
            SKY=gps.getSentence("SKY")
            if TPV is not None:
                if nofix:
                    print("Got fix after",time()-start)
                    nofix=False
                    print("TPV:",TPV)
                    print("SKY:",SKY)

            sleep(5)
    
    except KeyboardInterrupt:
        exit("cancelled")
