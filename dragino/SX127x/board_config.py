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

# Modified 2018-01-10 Philip Basford to be compatible with the dragino LoRa HAT
# modified 2024-08-09 Brian Norman to use pigpio on Bookworm 

import pigpio
import spidev
import time

GPIO=pigpio.pi()

class BOARD:
    """ 
	Board initialisation/teardown and pin configuration is kept here.
    This is the Raspberry Pi board with a Dragino LoRa/GPS HAT
    
    Note that the BCOM numbering for the GPIOs is used (pigpio default).
	and that these numbers work but don't match the User Manual PDF 
	we are using SPI channel 0 (default MOSI,MISO,SCLK)
	but the HAT uses GPIO2 for the CS
	
	NOTE ALSO the PIN values below are BCM numbers which pigpio uses
	"""
	
    RST = 11	# Pin 23
    DIO0 = 4    # Pin 7 
    DIO1 = 23   # Pin 16
    DIO2 = 24   # Pin 18
    DIO3 = None # Not connected on dragino header
    SPI_CS = 2  # Pin 3 - Chip Select pin to use
	
    # The spi object (channel 0) is kept here
    spi = None

    @staticmethod
    def setup():
        """ Configure the Raspberry GPIOs
        :rtype : None
        """
        print("Configuring GPIOs")
        
        # DIOx
        for gpio_pin in [BOARD.DIO0, BOARD.DIO1, BOARD.DIO2, BOARD.DIO3]:
            if gpio_pin is not None:
                GPIO.set_mode(gpio_pin, pigpio.INPUT)
                GPIO.set_pull_up_down(gpio_pin,pigpio.PUD_DOWN)
                
    @staticmethod
    def reset_radio():
        print("BOARD.reset_radio()")
        try:
            GPIO.set_mode(BOARD.RST,pigpio.OUTPUT)
            GPIO.write(BOARD.RST, pigpio.LOW)
            time.sleep(0.001) # must be > 100us
            GPIO.write(BOARD.RST, pigpio.HIGH)
            time.sleep(0.01) # chip needs 5ms to reset
        except Exception as e:
            print(f"Unable to reset the RFM95. Reason {e}")

    @staticmethod
    def teardown():
        """ Cleanup GPIO and SpiDev """
        print("\nClosing SPI")
        BOARD.spi.close()
        GPIO.stop()

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
        GPIO.callback(dio_number, pigpio.RISING_EDGE, callback)

    @staticmethod
    def add_events(cb_dio0, cb_dio1, cb_dio2, cb_dio3, cb_dio4, cb_dio5, switch_cb=None):
        if BOARD.DIO0 is not None:
            cb0=BOARD.add_event_detect(BOARD.DIO0, callback=cb_dio0)
        if BOARD.DIO1 is not None:
            cb1=BOARD.add_event_detect(BOARD.DIO1, callback=cb_dio1)
        if BOARD.DIO2 is not None:
            cb2=BOARD.add_event_detect(BOARD.DIO2, callback=cb_dio2)
        if BOARD.DIO3 is not None:
            cb3=BOARD.add_event_detect(BOARD.DIO3, callback=cb_dio3)

