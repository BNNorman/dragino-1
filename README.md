# Introduction

This is a clone of https://github.com/computenodes/LoRaWAN.git which ended development with the TTN V2.

This has been heavily modified to :-

* Support MAC V1.0.4 commands
* Support for frequency plans like AU915-928-FSB2
* Use threading timers to switch to listen on RX2 after RX1 delay if a valid message is not received in RX1.
* Changed user configuration file to TOML format
* Cache all TTN parameters
* Added flags to indicate if the system is transmitting
* added methods to get the last transmit air-time so that adherence to the LoRa duty cycle can be controlled

TODO

* support both class A & C operation (not class B)

# Lora Duty Cycle

This is not managed by the dragino code. However, your code can comply as follows (though could be better implemented)

```
# note this is just an outline
from time import sleep
from dragino import Dragino

D = Dragino("dragino.toml", logging_level=logLevel)

D.join()
while not D.registered():
 sleep(0.1)

message="hello world"

while True:
  D.send(message)

  while D.transmitting:
    sleep(0.1) # or do something useful

  airtime=D.lastAirTime()
  sleep(99*airtime)       # for a 1% duty cycle

```

# TTN Fair Use

TTN Fair Use limits you to a max of 30 seconds airtime in any 24 hour period though, according to Descartes "
concensus on the forum is that a downlink per fortnight is good design". 

There are a number of ways to do that and I'll leave it to your imagination.


# Downlink Messages

TTN Fair use policy limits you to 10 downlinks per 24 hour period.

This code does support passing unconfirmed/confirmed downlink messages to your handler. Checkout the test_downlink.
py example.

Be aware that your downlink handler is called during an interrupt and should not spend too much time fiddling about.
I recommend you push the information onto a queue and deal with the queue in a separate thread. Having said that you
are unlikely to experience a flood of downlinks. There is a recommended max of 10 per day with TTN.

The TTN servers only send downlinks after an uplink in accordance with the LoRaWAN spec so you need to setup a downlink before sending an uplink - remember that when testing.

See https://www.thethingsnetwork.org/docs/lorawan/classes/ for a complete description of LoRaWAN device classes.

Briefly, for class A device, downlink messages will only be sent after an uplink message. This is generally the type of device most people will be using as it consumes the least power on, for example, Arduino sensor devices. However, a Raspberry Pi + dragino HAT is constantly powered so when it isn't transmitting it can be always listening.

# Crypto

Added pycrypto master - instructions to install are in the zip file.

# LoRaWAN

This is a LoRaWAN v1.0 implementation in python for the Raspberry Pi Dragino LoRa/GPS HAT, it is currently being used to connect to the things network https://thethingsnetwork.org and is based on work from https://github.com/jeroennijhof/LoRaWAN

It also uses https://github.com/mayeranalytics/pySX127x.

See: https://www.lora-alliance.org/portals/0/specs/LoRaWAN%20Specification%201R0.pdf

## Hardware Needed
* Raspberry Pi
* SD card
* Dragino LoRa/GPS HAT - or make your own
* Raspberry Pi power supply

## Installation (Compute nodes version)
1. Install Raspbian on the Raspberry Pi
2. Enable SPI using raspi-config
3. Enable Serial using raspi-config (no login shell)
    1. check your serial ports 'ls /dev/serial*'
    2. check the serial port is receiving GPS data with 'cat /dev/serialx' where x is your port number.
4. Install the required packages `sudo apt install device-tree-compiler git python3-crypto python3-nmea2 python3-rpi.gpio python3-serial python3-spidev python3-configobj`
	1. python3-crypto is no longer available for bullseye but pycrypto can be installed with pip and is the same thing.
5. Download the git repo `git clone https://github.com/computenodes/LoRaWAN.git`
    1. make a copy of dragingo.ini.default `cp dragino.ini.default dragino.ini`
    2. make sure your dragino.ini is set to use the serial port from step 3
6. Enable additional CS lines (See section below for explanation)
    1. Change into the overlay directory `cd dragino/overlay`
    2. Compile the overlay `dtc -@ -I dts -O dtb -o spi-gpio-cs.dtbo spi-gpio-cs-overlay.dts`.  This might generate a couple of warnings, but seems to work ok
    3. Copy the output file to the required folder `sudo cp spi-gpio-cs.dtbo /boot/overlays/`
    4. Enable the overlay at next reboot `echo "dtoverlay=spi-gpio-cs" | sudo tee -a /boot/config.txt`
    5. Reboot the Pi `sudo reboot`
    6. Check that the new cs lines are enabled `ls /dev/spidev0.*` should output `/dev/spidev0.0  /dev/spidev0.1  /dev/spidev0.2`.  In which case the required SPI CS line now exists
7. Create a new device in The Things Network console and copy the details into the config file `dragino.ini`
8. Run the test programm `./test.py` and the device should transmit on the things network using OTAA authentication
9. run './test_downlink.py' to check downlink messages are received (after scheduling one in the TTN console)

## Additional Chip Select Details
For some reason the Dragino board does not use one of the standard chip select lines for the SPI communication.  This can be overcome by using a device tree overlay to configure addtional SPI CS lines.  I am not a device tree expert so I adapted the example given at https://www.raspberrypi.org/forums/viewtopic.php?f=63&t=157994 to provide the code needed for this to work.  

# GPSD #
If you are having problems with gpsd on the pi here's a few things to check.

Firstly, use cgps - it should show data coming from the GPS device. If not it may mean that gpsd hasn't identified the serial port being used. The port is /dev/ttyAMA0 which is owned by root and group is dialout. This port is setup by the RPi when you boot it up.

Secondly, I had to edit /etc/default/gpsd and ensure it has the line DEVICES=/dev/ttyAMA0 in it.

## Speculation follows ##
Quite possibly this is caused by a race condition when the Pi boots up. A similar thing happens on inserting a USB stick - it takes several seconds for the device to be mounted. So, if the Pi is booting and gpsd starts before /dev/ttyAMA0 has been created gpsd won't find it. Possibly the gpsd.service file could include a conditional clause to wait for /dev/ttyAMA0 to exist before proceeding. But hey, adding the device to the defaults file works.

# Caching #

The code reads initial configuration data from dragino.toml. If the device joins TTN the parameters are stored in cache.json.

Next time you reboot your device, the code looks for cache.json and takes it's parameters from there. In particular the devaddr indicates the device has joined TTN at some time and does not need to perform a join again.

However, if you want to force a rejoin just delete the cache.json file and reboot.

During operation TTN may send MAC commands down to the device to adjust some parameters (read the spec). The cache.json file will be updated when that happens so that, after a restart, the system can carry on where it left off.

