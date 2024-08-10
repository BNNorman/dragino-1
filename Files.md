# files.md

A brief description of the files

## dragino.toml

Contains the config information for TTN and the Dragino HAT. It supercedes the old dragino.ini and Frequncy.py files from the original code and provides a more complete Frequency Plan definition.

Much of the default TTN values are kept here but they are superceded by the contents of cache.json

## cache.json

Created on first run. Delete to force a re-join.

This is used by the software to cache the TTN data. As it's name suggests it is a JSON formatted text file.

When the code first starts it is populated from the dragino.toml settings. MAC commands from the TTN server may modify the cached values.

After an OTAA join the keys are stored here so that it is no longer necessary to join every time the code is restarted.

If this file is deleted the dragino code will attempt to join TTN next time it runs

## showCache.py

Displays the contents of the cache.json file.

## testTTN.py

A simple test which joins TTN and sends short messages till the TTN Fair Use Policy limit (30s) is reached. Assumes a duty cycle of 1% (EU).

## testDOWNLINK.py

A simple test to check downlinks are received. Before running this you MUST schedule a downlink message in the TTN console.

## testGPS.py

Checks that the code is receiving messages from gpsd. Use 'copsd' first to check that gpsd is actually receiving data. It may be a good idea to use an active antenna if running indoors.

# dragino folder

## Dragino.py

The main module which transmits and receives TTN messages. You need to create an instance of Dragino - see testTTN.py

## Config.py

Simply used to load the dragino.toml file into a dictionary which can be passed to other code which subsequently accesses it.

## GPShandler.py

GPS handling is done using GPSD to parse the GPS messages.

It uses threading to periodically sample the GPS TPV message. If a valid message is received it is cached with a timestamp.
This allows the Raspberry time to be synchronised with real world time.

Calls to get_gps() will return (lat, lon, timeStamp, lastGpsTimeReading). Ot (None,None,None,None) until gps data is available.

The timestamp allows the caller to calculate the callers' actual time as follows :-

```
current_time=lastGpsTimeReading+(now()-timeStamp)
```

## LICENSE.txt

The licence was provided by the original author computenodes and continues to apply

## MAChandler.py

On startup this module gets the default TTN parameters from dragino.toml which is read and passed in as dragino.py starts. If cache.json doesn't exist it is created with the default parameters.

If the end device receives MAC commands, from the server, which modify those parameters then the cache.json is updated by this module.

There are only two MAC uplink messages which can originate from the end device: linkCheckReq and timeReq. All others come from the server and require an acknowledgment in the next uplink.

Assuming you have instantiated Dragino like this:
```
from dragino import Dragino
D=Dragino(...)
```
the MAC commands can be added to the next uplink with:-
```
D.MAC.link_check_req()
D.MAC.time_req()
```

The time_req is not very useful since the returned value does not compensate for network latency.

The LoRaWAN V1.0.x specification states that multiple MAC commands may occur in a message occupying up to 16 bytes in total. The MAC handler places commands and replies into a list. When dragino.py requests the list with D.MAC.getFOpts() the list is cleared so that it isn't sent with all uplink messages.

## reset.py

A legacy program which resets the radio hardware. I have never needed to use this.

## Strings.py

Used by other modules to ensure variable name capitalisation is uniform.

# dragino/LoraWan

For the most part the files in this folder were the standard file from computenodes but have been updated for Bookworm. They tend to lack useful comments. The following have been modified :-

## FHDR.py

Modified to accept an FOpts parameter when the create() method is called like this:-
```
lorawan.create(MHDR.UNCONF_DATA_UP, {
            'devaddr': devaddr,
            'fcnt': FCntUp,
            'data': message,
            'fport=':1,
            'fopts':FOpts})

```
## MACpayload.py

Modified to allow the LoRaWAN port number to be changed from the default of 1. See FHDR.py example above.

# dragino/SX127x

The files in this folder are the standard file from computenodes modified for Bookworm. 
