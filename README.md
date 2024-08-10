# IMPORTANT

This code has been modified to run on the RPI Bookworm OS. ALL pip installs MUST be done with a Python virtual env activated.


# Introduction

The Dragino Pi HAT includes GPS and an RFM95 (sx127x) radio. This configuration allows you to send sensor readings to a TTN application using a Raspberry Pi.

GPS is disabled by default.

Testing was done using a Dragino Lora/GPS Pi HAT V1.4 on a Pi 4 with Bookworm installed. It should also work on a Dragino Lora/GPS HAT V1.3 - earlier is not recommended if you want to just use the device for LoRa only comms.

See installation.md if you want to get started quickly.

This is a clone of https://github.com/computenodes/LoRaWAN.git which ended development with the TTN V2. It has been updated to work with Bookworm on the Pi and, the current, TTN V3.

The changes made:-

* Support MAC V1.0.4 commands
* Support for frequency plans like AU915-928-FSB2
* Use threading timers to switch to listen on RX2 after RX1 delay if a valid message is not received in RX1.
* Changed user configuration file to TOML format
* Cache all TTN parameters in the file cache.json - which is created on first run.
* added methods to get the last transmit air-time so that adherence to the LoRa duty cycle can be controlled
* adhering to the TTN Fair Use Policy requires you to add your own code. 

TODO

* support both class A & C operation (not class B)


# Radio Support

Currently the code only supports the RFM95 (sx127x) module which comes with the Dragino Lora/GPS HAT.

# Lora Duty Cycle

This is not managed by the dragino code. 

Look at testTTN.py to see how I did it.

# TTN Fair Use Policy (FUP)

The TTN FUP limits you to a max of 30 seconds airtime in any 24 hour period. Please respect it when using the free system. If you need more you'll need a commercial agreement.

testTTN.py includes code to stop transmitting when the TTN FUP (30s tx time) has been reached. Ideally you would want to use a sliding window (queue) so that transmission can restart when the 24hour window closes.

## Downlink Messages

TTN Fair use policy limits you to 10 downlinks per 24 hour period though, according to Descartes, "concensus on the forum is that a downlink per fortnight is good design"

Note that downlink messages eat into the gateway duty cycle. Also, sending confirmed uplinks requires a downlink. So avoid doing that at all costs if you can. To prove you have connectivity just force a re-join.

This code does support passing unconfirmed/confirmed downlink callback messages to your handler. Checkout the test_downlink.py example.

Be aware that your downlink handler is called during an interrupt and should not spend too much time fiddling about. The dragino code already has a lot to do. Fortunately, we don't receive loads of downlinks so we probably have time on our side.

I recommend you push the downlink information onto a queue and deal with the queue in a separate thread.

The TTN servers only send downlinks after receiving an uplink, in accordance with the LoRaWAN spec, so you need to setup a downlink before sending an uplink - please remember that when testing.

# Device classes

See https://www.thethingsnetwork.org/docs/lorawan/classes/ for a complete description of LoRaWAN device classes.

Briefly, for class A device, downlink messages will only be sent after an uplink message. This is generally the type of device most people will be using as it consumes the least power, for example, on Arduino sensor devices. However, a Raspberry Pi + dragino HAT is constantly powered so when it isn't transmitting it can be always listening and so is, effectively, a class C device.

# Encryption

The previous version of my code used the old Python Crypto package which is no-longer supported.

However, with Bookworm, PyCrytodome is already installed.

Pycriptodome is a maintained fork of PyCrypto used with Bookworm. The LORAWAN files have been changed to use PyCryptodome.


# LoRaWAN

This code is a LoRaWAN v1.0 implementation in python for the Raspberry Pi Dragino LoRa/GPS HAT, it is currently being used to connect to the things network https://thethingsnetwork.org and is based on work from https://github.com/jeroennijhof/LoRaWAN

It also uses https://github.com/mayeranalytics/pySX127x (Sorry, not the sx126x as the dragino HAT is sx127x)

See: https://www.lora-alliance.org/portals/0/specs/LoRaWAN%20Specification%201R0.pdf
