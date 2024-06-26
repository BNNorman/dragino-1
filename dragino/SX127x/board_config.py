""" Defines the BOARD class that contains the board pin mappings. """

# Copyright 2015 Mayer Analytics Ltd.
#
# This file is part of pySX127x.
#
# pySX127x is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public
# License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# pySX127x is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more
# details.
#
# You can be released from the requirements of the license by obtaining a commercial license. Such a license is
# mandatory as soon as you develop commercial activities involving pySX127x without disclosing the source code of your
# own applications, or shipping pySX127x with a closed source product.
#
# You should have received a copy of the GNU General Public License along with pySX127.  If not, see
# <http://www.gnu.org/licenses/>.

#Modified 2018-01-10 Philip Basford to be compatible with the dragino LoRa HAT
import RPi.GPIO as GPIO
import spidev

import time



class BOARD:
    """ Board initialisation/teardown and pin configuration is kept here.
        This is the Raspberry Pi board with a Dragino LoRa/GPS HAT
    """
    # Note that the BCOM numbering for the GPIOs is used.
    RST = 11
    DIO0 = 4   # RaspPi GPIO 4
    DIO1 = 23   # RaspPi GPIO 23
    DIO2 = 24   # RaspPi GPIO 24
    DIO3 = None # Not connected on dragino header
    LED  = 18   # RaspPi GPIO 18 connects to the LED on the proto shield
    SWITCH = 4  # RaspPi GPIO 4 connects to a switch
    SPI_CS = 2  # Chip Select pin to use
    # The spi object is kept here
    spi = None

    @staticmethod
    def setup():
        """ Configure the Raspberry GPIOs
        :rtype : None
        """
        print("Configuring GPIOs")
        GPIO.setmode(GPIO.BCM)
        # LED
        GPIO.setup(BOARD.LED, GPIO.OUT)
        GPIO.output(BOARD.LED, 0)
        
        # switch
        GPIO.setup(BOARD.SWITCH, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) 
        # DIOx
        for gpio_pin in [BOARD.DIO0, BOARD.DIO1, BOARD.DIO2, BOARD.DIO3]:
            if gpio_pin is not None:
                GPIO.setup(gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        # blink 2 times to signal the board is set up
        BOARD.blink(.1, 2)

    @staticmethod
    def reset_radio():
        print("BOARD.reset_radio()")
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(BOARD.RST,GPIO.IN)
            GPIO.setup(BOARD.RST,GPIO.OUT)
            GPIO.output(BOARD.RST, GPIO.LOW)
            time.sleep(0.001) # must be > 100us
            GPIO.output(BOARD.RST, GPIO.HIGH)
            time.sleep(0.01) # chip needs 5ms to reset
            GPIO.cleanup()
        except:
            print("Unable to reset the RFM95")

    @staticmethod
    def teardown():
        """ Cleanup GPIO and SpiDev """
        print("\nClosing SPI")
        BOARD.spi.close()
        GPIO.cleanup()

    @staticmethod
    def SpiDev(spi_bus=0, spi_cs=SPI_CS):
        """ Init and return the SpiDev object
        :return: SpiDev object
        :param spi_bus: The RPi SPI bus to use: 0 or 1
        :param spi_cs: The RPi SPI chip select to use: 0 or 1
        :rtype: SpiDev
        """
        BOARD.spi = spidev.SpiDev()
        BOARD.spi.open(spi_bus, spi_cs)
        print("BOARD SpiDev created")
        return BOARD.spi

    @staticmethod
    def add_event_detect(dio_number, callback):
        """ Wraps around the GPIO.add_event_detect function
        :param dio_number: DIO pin 0...5
        :param callback: The function to call when the DIO triggers an IRQ.
        :return: None
        """
        GPIO.add_event_detect(dio_number, GPIO.RISING, callback=callback)

    @staticmethod
    def add_events(cb_dio0, cb_dio1, cb_dio2, cb_dio3, cb_dio4, cb_dio5, switch_cb=None):
        if BOARD.DIO0 is not None:
            BOARD.add_event_detect(BOARD.DIO0, callback=cb_dio0)
        if BOARD.DIO1 is not None:
            BOARD.add_event_detect(BOARD.DIO1, callback=cb_dio1)
        if BOARD.DIO2 is not None:
            BOARD.add_event_detect(BOARD.DIO2, callback=cb_dio2)
        if BOARD.DIO3 is not None:
            BOARD.add_event_detect(BOARD.DIO3, callback=cb_dio3)
        # the modtronix inAir9B does not expose DIO4 and DIO5
        if switch_cb is not None:
            GPIO.add_event_detect(BOARD.SWITCH, GPIO.RISING, callback=switch_cb, bouncetime=300)

    @staticmethod
    def led_on(value=1):
        """ Switch the proto shields LED
        :param value: 0/1 for off/on. Default is 1.
        :return: value
        :rtype : int
        """
        GPIO.output(BOARD.LED, value)
        return value

    @staticmethod
    def led_off():
        """ Switch LED off
        :return: 0
        """
        GPIO.output(BOARD.LED, 0)
        return 0

    @staticmethod
    def blink(time_sec, n_blink):
        if n_blink == 0:
            return
        BOARD.led_on()
        for i in range(n_blink):
            time.sleep(time_sec)
            BOARD.led_off()
            time.sleep(time_sec)
            BOARD.led_on()
        BOARD.led_off()
