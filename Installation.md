# Installation

This procedure is for Bookworm but may work on earlier OS versions provided you install PyCryptodome and pigpio. RPi.GPIO does not enable edge detection (for radio interrupts) unless you run as root hence pigpio is now used.

## Hardware Needed
* Raspberry Pi 4 but should work on any Pi that supports Bookworm (Not tested)
* SD card for OS
* Dragino LoRa/GPS HAT V1.4 (1.3 should work) or make your own using the same pins (see LoRa_GPS_HAT_UserManual_v1.0.pdf)
* Raspberry Pi power supply

# Installation for Bookworm.

## Pi Setup

1. Install Bookworm on the Raspberry Pi SD Card, boot it and update (if necessary).
   NOTE: using the rpi-imager tool allows you to setup your WiFi/login etc beforehand if you want to.
   
2. Enable SPI using 
```
sudo raspi-config
```

3. Enable the additional CS line (The Dragino HAT doesn't use the standard chip select lines)
    a. Change into the overlay directory 
	```
		`cd dragino/overlay`
	```	
    b. Compile the overlay  with 
	```
		`dtc -@ -I dts -O dtb -o spi-gpio-cs.dtbo spi-gpio-cs-overlay.dts`.
	```	
	
	This worked without any warnings on my Pi 4
	
    c. Copy the output file to the required folder 
	```
		`sudo cp spi-gpio-cs.dtbo /boot/overlays/`
	```	
    d. Enable the overlay at next reboot 
	```
		`echo "dtoverlay=spi-gpio-cs" | sudo tee -a /boot/firmware/config.txt`
	```	
    e. Reboot the Pi
    f. Check that the new cs lines are enabled 
	```
		`ls /dev/spidev0.*` 
	```
	This should output 
	```
	`/dev/spidev0.0  /dev/spidev0.1  /dev/spidev0.2`.  
	```
	    In which case the required SPI CS line 0.2 now exists


## GPIO

RPi.GPIO, which the original code used, appears to be broken after Buster - the code fails to add edge detection required to detect DIO changes from the Radio unless run as root. (not good).

I have modified the code to use pigpio instead. pipgpio is pre-installed in Bookworm. However, you need to enable the pigpiod daemon for it to work:-

```
sudo systemctl enable pigpiod

```

Thereafter pigpiod will reload on reboot. If you don't want to wait for a reboot you can start pigpiod with:-

```
sudo systemctl start pigpiod
```


# Virtual Environment

Bookworm will only install 'externally managed' packages using pip *IF* installed in an active virtual environment so you must create one with:-

```
python -m venv ~/dvenv  # or any name you wish - a shorter name is better as you will be typing it later

```

then activate it with :-

```
source ~/dvenv/bin/activate
```

Your login prompt will change to :-

```
(dvenv)<yourid>@<hostname>:~ $
```

You will have to activate the venv every time you logout/in/power cycle/ before you start the dragino program.

## Additional packages

Now you can install the required additional packages:-

```
pip install spidev # required to communicate with the Radio.
pip install gps3   # required for GPS
```

# GPSD
Bookworm already includes gpsd GPS operation so you just need to enable the daemon

```
sudo systemctl enable gpsd
```

To check it is working run cgps. You will see a screen showing what data is being collected. Note that it could take up to a minute for the GPS to lock onto some satellites. An active antenna improves the reception A LOT.
```
cgps
```


# Dragino source code

You'll find the latest dragino version here:-

https://github.com/BNNorman/dragino-1

Install this, preferably,into your virtual environment but once you have activated your environment it will run from wherever you copied it to.


## dragino.toml and cache.json

dragino.toml provides the initial settings when you first start the code running (You will need a TTN app set up first)
cache.json is where the code stores the settings it uses from dragino.toml. cache.json values can be overwritten by downlink MAC commands from the server.

If cache.json contains a devaddr it means your device has joined the network. If that is the case the dragino code will not attempt to join TTN but will use the cached keys etc.

If you want to rejoin TTN simply delete cache.json before you run your program.


# TTN setup

1. Create a new device in The Things Network console and copy the device details into the config file `dragino.toml`
    1. edit dragino.toml and add your device keys (OTAA is preferred)

2. Run the test program 
``` 
python testTTN.py
``` 
and the device should transmit on the things network using OTAA authentication until it reaches the TTN FUP tx limit.

3. run the downlink test program
``'
python testDOWNLINK.py
```

to check downlink messages are received after scheduling one in the TTN console first

# Using GPS

Run the testGPS script to check that GPS values are being seen.

```
python testGPS.py
```

## enabling GPS

GPS is disabled by default (requested by users). To enable the code to communicate with gpsd you need to use:-

```
D=Dragino("dragino.toml",logging_level=loglevel,enableGPS=True)
```

Thereafter you can get the lat,lon,timestamp and lastGpsReading as follows:-

```
(lat,lon,timestamp,lastGpsReading)=G.get_gps() 

```

This will be (None,None,None,None) until a GPS lock has been achieved. These values are cached, since we aren't expecting the device to move around, so you may need to correct the timestamp.


GPS isn't fast. When you receive a timestamp it could be adrift by a few seconds so the following function attempts to compensate for that using timestamp and lastGpsReading:-

```
corrected_datetime=D.get_corrected_timestamp()

```












