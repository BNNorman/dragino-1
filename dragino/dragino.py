#!/usr/bin/env python3
"""
Basic interface for dragino LoRa/GPS HAT
Copyright (C) 2018 Philip Basford

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import logging

from random import randrange
from .SX127x.LoRa import LoRa, MODE
from .SX127x.board_config import BOARD
from .SX127x.constants import BW
from .LoRaWAN import new as lorawan_msg
from .LoRaWAN import MalformedPacketException
from .LoRaWAN.MHDR import MHDR

from time import time
from .MAChandler import MAC_commands
from .Config import TomlConfig
from .Strings import *
import threading
from .GPShandler import GPS
import traceback


# Dragino.py is called from classes in the
# parent directory. It helps to add that to the system path
import os
import sys
currentDir=os.path.dirname(os.path.realpath(__file__))
parentDir=os.path.dirname(currentDir)
sys.path.append(parentDir)

#################################
DEFAULT_LOG_LEVEL = logging.DEBUG 	# Change after finishing development
DEFAULT_RETRIES = 3 				# How many attempts to send the message


class radioSettings:
    # used by configureRadio
    JOIN=0
    SEND=1
    RX1=2
    RX2=3

class DraginoError(Exception):
    """
        Error class for dragino class
    """


class Dragino(LoRa):
    """
        Class to provide an interface to the dragino LoRa/GPS HAT
    """
    def __init__(
            self, config_filename,
            logging_level=DEFAULT_LOG_LEVEL,
            enableGPS=False
            ):

        self.confirmWithNextUplink=False # for confirmed data down

        self.logger = logging.getLogger("Dragino")
        self.logger.setLevel(logging_level)

        self.logger.info("__init__ starting")

        """
            Create the class to interface with the board
        """

        BOARD.setup()
        
        super(Dragino, self).__init__() # LoRa init

        self.TC=TomlConfig(config_filename)                 # load user config
        self.config=self.TC.getConfig()                     # get the config dictionary
        self.MAC=MAC_commands(self.config,logging_level)    # loads cached MAC info (if any) otherwise config values

        # setup GPS
        if enableGPS:
            self.logger.info("enabling GPS")
            self.GPS=GPS(logging_level,self.config[GPSD]["threaded"],self.config[GPSD]["threadLoopDelay"])
        else:
            self.logger.warning("Not enabling GPS (see enableGPS param)")
            self.GPS=None

        try:
            """
            if config file contains strings where numbers are expected we get and error:-
            
            "...unsupported operand type(s) for <<: 'str' and 'int'"
            
            """

            self.set_mode(MODE.HF_LORA_SLEEP)
            self.set_dio_mapping([1, 0, 0, 0, 0, 0]) # listening


            self.set_sync_word(self.config[TTN][SYNC_WORD])
            self.set_rx_crc(self.config[TTN][RX_CRC])

            self.joinRetries=self.config[TTN][JOIN_RETRIES]

            self.frequency_plan=self.config[TTN][FREQUENCY_PLAN]


        except Exception as e:
            self.logger.error(f"error initialising radio config {e}. Check config values are not strings")

        self.set_agc_auto_on(1)
        
        # for downlink DATA messages
        self.downlinkCallback=None
        
        # status
        self.transmitting=False
        self.validMsgRecvd=False     # used to detect valid msg receive in RX1
        self.txStart=None          # used to compute last airTime
        self.txEnd=None

        self.logger.info("__init__ done")

    def setDownlinkCallback(self,func=None):
        """
        Configure the callback function which will receive
        two parameters: decodedPayload and mtype.

        decodedPayload will be a bytearray.
        mtype will be MHDR.UNCONF_DATA_DOWN or MHDR.CONF_DATA_DOWN.

        See test_downlink.py for usage.

        func: function to call when a downlink message is received
        """
        if hasattr(func,'__call__'):
            self.logger.info("Setting downlinkCallback to %s",func)
            self.downlinkCallback=func
        else:
            self.logger.info("downlinkCallback is not callable")


    def configureRadio(self,cfg):
        """
        change radio settings

        called whenever there's a change of radio settings

        :param cfg: (see radioSettings class)
        """
        freq,sf,bw=0,0,0

        if cfg==radioSettings.JOIN:
            freq,sf,bw=self.MAC.getJoinSettings()
        elif cfg==radioSettings.SEND:
            freq,sf,bw=self.MAC.getSendSettings()
        elif cfg==radioSettings.RX1:
            freq,sf,bw=self.MAC.getRX1Settings()
        elif cfg==radioSettings.RX2:
            freq,sf,bw=self.MAC.getRX2Settings()

        self.logger.info(f" freq={freq} sf={sf} bw={bw}")

        self.set_pa_config(
            pa_select=1,
            max_power=self.config[TTN][MAX_POWER],
            output_power=self.config[TTN][OUTPUT_POWER]
            )
   
        # now configure the radio
        self.set_mode(MODE.HF_LORA_SLEEP)
        self.set_freq(freq)
        self.set_spreading_factor(sf)
        self.set_bw(bw)
        self.set_mode(MODE.HF_LORA_RXCONT)


    def switchToRX2(self):
        """
            called by threading timer elapsing after rx1_delay+1 following
            a transmission

            device remains listening in rx2 until the next transmission
        """
        self.logger.info("switching to RX2")

        # set by on_rx_done() when a valid message
        # has been received during RX1 or RX2
        if self.validMsgRecvd:
            self.logger.info("Message was received in RX1 already.")
            return

        self.configureRadio(radioSettings.RX2)

    def getDataRate(self):
        """
        returns the current data rate 1..6 which corresponds
        to sf7..sf12 at 125kHz
        """
        return self.MAC.getDataRate()

    def process_JOIN_ACCEPT(self,rawPayload):
        """
        downlink is a join accept message
        """
        self.logger.debug("Trying to process JOIN_ACCEPT")
        try:
            appkey=self.MAC.getAppKey()
            lorawan = lorawan_msg([], appkey)
            lorawan.read(rawPayload)
            decodedPayload=lorawan.get_payload()
            lorawan.valid_mic() # throws an exception if MIC not valid

            self.logger.debug(f"decoded JOIN_ACCEPT payload {decodedPayload}")

            self.MAC.setLastSNR(self.get_pkt_snr_value()) # used for last status req

        except Exception as e:
            # if decoding failed it probably isn't a valid lorawan packet
            self.logger.exception(f"Invalid JOIN_ACCEPT: {e}")
            return

        # if we receive a valid message in RX1 we don't need
        # to switch to RX2
        self.validMsgRecvd=True

        # values from the JOIN_ACCEPT payload
        # spec says payload is
        # join_nonce:3,netId:3;devaddr:4,DL_settings:1,RX_delay:1,cfList:16 (optional)

        frm_payload=lorawan.get_mac_payload().get_frm_payload()


        self.MAC.setRX1Delay(frm_payload.get_rxdelay())
        self.MAC.setDLsettings(frm_payload.get_dlsettings())


        # cflist is optional.
        # it defines the 5 additional lora frequencies following the
        # 3 standard join frequencies.
        # I found this delivers the same frequencies in the config toml
        # lora_freqs[3..7] which came from the TTN frequency plan
        # Un-comment the following lines
        # to use
        # cflist=frm_payload.get_cflist())
        # self.MAC.handleCFlist(cflist)

        devaddr=lorawan.get_devaddr()
        nwkskey=lorawan.derive_nwskey(self.devnonce)
        appskey=lorawan.derive_appskey(self.devnonce)


        self.MAC.setDevAddr(devaddr)
        self.MAC.setNwkSKey(nwkskey)
        self.MAC.setAppSKey(appskey)

        self.logger.debug(f"devaddr: {devaddr}")
        self.logger.debug(f"nwkskey: {nwkskey}")
        self.logger.debug(f"appskey: {appskey}")

        self.MAC.setFCntUp(1)

        # cache changed values
        self.MAC.saveCache()

        # finally process any MAC commands (if any)
        #self.MAC.handleCommand(lorawan.get_mac_payload())

    def process_DATA_DOWN(self,rawPayload):
        """
        downlink messages can be unconfirmed or confirmed

        Optional parts enclosed in [] byte count enclosed in ()

        rawPayload=MHDR(1),DEVADDR(4),FCTL(1),FCNT(2),[FOPTS(1..N)],[FPORT(1)],[FRM_PAYLOAD(..N)],MIC(4)

        To detect if optional parts exist we need to calc the length
        FOpts & 0x0F tells us the length of any FOPTS

        """
        try:
            self.logger.debug("Downlink data received")

            mtype=rawPayload[0] & 0xF0

            # check if just MAC commands
            rawPayloadLen=len(rawPayload)

            FOptsLen=rawPayload[5] & 0x0F

            # message format - only FRM_PAYLOAD (if any) is encoded in MAC 1.0.x
            # parts enclosed in [] are optional. Size in bytes is enclosed in ()
            # MHDR(1),DEVADDR(4),FCTL(1),FCNT(2),[FOpts(1..N)] [FPort(1)],[FRM_PAYLOAD(1..N)],MIC(4)

            msgSize=12 + FOptsLen # excluding FPort & FRM_PAYLOAD

            if (rawPayloadLen-msgSize)==0:
                self.logger.info("rawPayload does not have a FRMpayload or FPort")
                self.MAC.processFopts(rawPayload[8:8+FOptsLen])
                return

            # looks like a proper downlink with data sent to me
            # so lets try to understand it
            nwkskey=self.MAC.getNwkSKey()
            appskey=self.MAC.getAppSKey()

            lorawan = lorawan_msg(nwkskey,appskey)
            lorawan.read(rawPayload)

            decodedPayload=lorawan.get_payload() # must call before valid_mic()
            lorawan.valid_mic()

            self.validMsgRecvd=True

            self.MAC.setLastSNR(self.get_pkt_snr_value()) # used for MAC status reply

            if self.downlinkCallback is not None:
                self.downlinkCallback(decodedPayload,mtype,lorawan.get_mac_payload().get_fport())

            # finally process any MAC commands
            self.MAC.handleCommand(lorawan.get_mac_payload())

            # we may need to ACK
            if mtype==MHDR.CONF_DATA_DOWN:
                self.confirmWithNextUplink=True

        except Exception as e:
            self.logger.debug(f"Error processing downlink mtype={mtype} error was {e}.")


    def on_rx_done(self):
        """
            Callback on RX complete, signalled by I/O

            Several calls may throw errors, we ignore the payload if any occur
        """
        self.clear_irq_flags(RxDone=1)
        self.logger.debug("Received message...")

        # read the payload from the radio
        # this may or may not be a valid lorawan message
        rawPayload = self.read_payload(nocheck=True)
        decodedPayload=bytearray() # keeps the compiler happy

        if rawPayload is None:
            self.logger.debug("rawPayload is None")
            return

        # 12 bytes is the absolute minimum rawPayload length
        if len(rawPayload)<12:
            self.logger.debug(f"received invalid message. Too small.")
            return

        self.logger.debug(f"raw payload {rawPayload}")

        # MHDR is not encoded and is first byte of the rawPayload
        mtype=rawPayload[0] & 0xE0

        if mtype==MHDR.JOIN_ACCEPT:
            self.process_JOIN_ACCEPT(rawPayload)
            return

        # don't process any other messages till we have registered
        # since we don't have the keys to decode FRM payloads they may
        # come from dubious sources
        if not self.registered():
            self.logger.debug(f"received a message mtype={mtype} but we haven't joined yet. Ignored")
            return

        # check the devaddr
        if list(reversed(rawPayload[1:5]))!=self.MAC.getDevAddr():
            # message is not for me
            self.logger.info("downlink message is not addressed to me")
            return

        # process any other downlink messages
        if mtype==MHDR.UNCONF_DATA_DOWN or mtype==MHDR.CONF_DATA_DOWN:
            self.process_DATA_DOWN(rawPayload)
            return

        self.logger.debug(f"Unhandled mtype {mtype}. Message ignored.")
        return


    def lastAirTime(self):
        """
            return the duration of the last transmission
            enables user to adhere to LoRa & TTN rules

        :return: time of last transmission or 0 (none)

        """
        if self.txStart is not None and self.txEnd is not None:
            return self.txEnd-self.txStart
        return 0

    def on_tx_done(self):
        """
            ISR. Callback on TX complete.

            Switch immediately to RX1 and set timers to switch to RX2 or retry
            join if no reply.

        """
        self.clear_irq_flags(TxDone=1)
        self.txEnd=time()               # enables computation of actual TX time
        self.transmitting=False         # let callers know we are done
        self.validMsgRecvd=False        # waiting for valid downlink msg
        self.set_mode(MODE.HF_LORA_STDBY)
        self.set_dio_mapping([0, 0, 0, 0, 0, 0])
        self.set_invert_iq(1)
        self.reset_ptr_rx()

        # RX1 settings can be changed by MAC commands
        self.logger.info("switching to RX1")
        self.configureRadio(radioSettings.RX1)

        # set a timer ready to switch to RX2 after rx1_delay + rx_window (normally 1 second)
        # this may not be accurate and delay may need to be slightly smaller
        delay=self.MAC.getRX1Delay()+self.config[TTN][RX_WINDOW]
        self.logger.info(f"setting timer delay {delay} to switch to RX2")

        t1=threading.Timer(delay,function=self.switchToRX2)
        t1.start()

        # check if retries have expired
        # this will be the case for a normal packet send after joining

        if self.join_retries==0:
            return

        # if we never receive a JOIN_ACCEPT we should retry
        t2=threading.Timer(self.config[TTN][JOIN_TIMEOUT],function=self._retryJoin)
        t2.start()

    def _retryJoin(self):
        """
        called by a thread timer after a timeout waiting for a JOIN_ACCEPT

        """
        if self.registered():
            return

        self.logger.info(f"retrying join  # {self.join_retries}")

        if self.join_retries>0:
            self.join_retries-=1
            self._tryToJoin()

    def getFcntUp(self):
        '''
        returns the Fcnt for uplinks. The limit is 65535 after that the LoRaWAN code
        will throw an error which can only be fixed by rejoining TTN
        '''
        return self.MAC.getFCntUp()

    def join(self):
        """
        try to join TTN

        The join frequency is randomly chosen from the first three frequencies
        in the frequency plan.

        NOTE: bandwidth (BW) range is defined in dragino/SX127x/constants.py and is essentially
        an int in range 0..9 determined by the radio not TTN but limited by TTN

        """

        # have we already joined?
        # this will be true if using ABP
        if self.registered():
            self.logger.info("Already joined, nothing to do")
            return

        mode=self.config[TTN][AUTH_MODE]

        if mode != AUTH_OTAA:
            self.logger.error(f"Unknown auth_mode {mode}")
            return

        self.logger.info("Performing OTAA Join")

        self.configureRadio(radioSettings.JOIN)

        self.join_retries=self.config[TTN][JOIN_RETRIES]

        return self._tryToJoin()


    def _tryToJoin(self):
        """
            Perform the OTAA auth in order to get the keys required to transmit
        """
        self.logger.info("trying to join TTN")
        if self.registered():
            self.logger.debug("already joined")
            return

        self.devnonce = [randrange(256), randrange(256)] #random devnonce 2 bytes

        appkey=self.MAC.getAppKey()
        appeui=self.MAC.getAppEui()
        deveui=self.MAC.getDevEui()
        self.logger.debug(f"App key = {appkey}")
        self.logger.debug(f"App eui = {appeui}")
        self.logger.debug(f"Dev eui = {deveui}")
        self.logger.debug(f"Devnonce= {self.devnonce}")

        lorawan = lorawan_msg(appkey)

        lorawan.create(
                    MHDR.JOIN_REQUEST,
                    {'deveui': deveui, 'appeui': appeui, 'devnonce': self.devnonce})

        packet=lorawan.to_raw()
        self.write_payload(packet)

        self.logger.debug(f"sending packet {packet}")
        self.set_mode(MODE.HF_LORA_TX)
        self.transmitting=True
        self.validMsgRecvd=False
        # used to calculate air time
        self.txStart=time()
        self.txEnd=None


    def getDutyCycle(self,freq=None):
        """
        returns the current duty cycle

        returns None if duty cycle is not in the valid range
        """
        return self.MAC.getMaxDutyCycle(freq)

    def registered(self):
        """
            return True if we have a device address.
            For ABP this is hard coded for OTAA
            it exists if we have joined.
            NOTE: this is also cached so a rejoin is not
            necessary following a power cycle and join() will
            return without trying to join.
            To force a re-join and startup delete the MAC cache
            file.
        """

        self.logger.info(f"checking if already registered.")

        try:

            devaddr=self.MAC.getDevAddr()

            self.logger.info(f"devaddr {devaddr} len {len(devaddr)}.")

            # dev address is always 4 bytes
            if len(devaddr)!=4:
                self.logger.debug("invalid devaddr != 4 bytes")
                return False

            if devaddr==[0x00, 0x00, 0x00, 0x00]:
                self.logger.debug("devaddr not assigned ")
                return False

            # TTN devaddr always starts 0x26 or 0x27
            if not devaddr[0] in self.config[DEV_ADDR][VALID_DEVADDR]:
                self.logger.debug(f"Invalid TTN devaddr {devaddr}, should begin with [VALID_DEVADDR]")
                return False

            self.logger.info("Already registered")
            return True

        except Exception as e:
            self.logger.info(f"whilst checking devaddr {devaddr} error was {e}")
            traceback.print_exception(e)
            return False

    def _sendPacket(self,message,port=1):
        """
        Send the uplink message and any MAC replies

        Used by normal uplink messages. See _tryToJoin() for actual joining.

        We always use a random frequency for sending.

        :param message: bytearray
        :param port: 1..254
        """

        try:

            # check if joined
            if not self.registered():
                self.logger.warn("attempt to send uplink but not joined")
                return

            # disable retry timeout
            self.join_retries=0

            self.configureRadio(radioSettings.SEND)

            nwkskey=self.MAC.getNwkSKey()
            appskey=self.MAC.getAppSKey()
            lorawan = lorawan_msg(nwkskey,appskey)

            try:

                FCntUp=self.MAC.getFCntUp()
                if FCntUp is None:
                    FCntUp=0
            except:
                FCntUp=0

            devaddr=self.MAC.getDevAddr()
            FOpts,FOptsLen=self.MAC.getFOpts() # can be an empty bytearray

            #lorawan.create(MHDR.UNCONF_DATA_UP, {'devaddr': devaddr, 'fcnt': FCntUp, 'data': message})
            if FOptsLen>0:
                lorawan.create(MHDR.UNCONF_DATA_UP,{
                    'devaddr': devaddr,
                    'fcnt': FCntUp,
                    'data': message,
                    'fport':port,
                    'fopts':FOpts})
            else:
                FCtrl=0;
                if self.confirmWithNextUplink:
                    self.confirmWithNextUplink=False
                    FCtrl=0x20 # bit 5 is an ACK
                # we never send confirmed up so the last downlink must have come from the server
                # if someone accidentally set the confirmed checkbox on the V3 messaging
                # panel
                lorawan.create(MHDR.UNCONF_DATA_UP,
                {'devaddr': devaddr, 'fcnt': FCntUp, 'data': message, 'fport': port, 'fctrl': FCtrl})

            self.MAC.setFCntUp(FCntUp+1)

            # encode the packet
            raw_payload=lorawan.to_raw()

            # load into radio fifo
            self.write_payload(raw_payload)
            self.logger.debug(f"Sending packet raw payload = {raw_payload}")

            self.set_dio_mapping([1, 0, 0, 0, 0, 0])

            self.transmitting=True
            self.validMsgRecvd=False
            self.set_mode(MODE.HF_LORA_TX)
            # used to calculate air time
            self.txStart=time()
            self.txEnd=None

        except ValueError as err:
            self.logger.exception(err)
            self.logger.error(f"Value error {err}")  # was: raise DraginoError(str(err)) from None

        except KeyError as err:
            self.logger.error(err)

        except Exception as exp:
            #self.logger.error(f"packet error {exp}")
            self.logger.exception(exp)


    def send_bytes(self, message,port=1):
        """
            Send a list of bytes over the LoRaWAN channel

            called by send("message") to create a byte array or directly if message
            is already a byte array
        """
        attempt = 0
        if self.MAC.getNwkSKey() is None or self.MAC.getAppSKey() is None:
            self.logger.error("no nwkSKey or AppSKey")
            return

        self._sendPacket(message,port)


    def send(self, message, port=1):
        """
            Send a string message over the channel
        """
        self.send_bytes(list(map(ord, str(message))),port)

    def get_gps(self):
        if self.GPS is None:
            self.logger.warning("GPS is disabled")
            return None
        return self.GPS.get_gps()

    def get_corrected_timestamp(self):
        if self.GPS is None:
            self.logger.warning("GPS is disabled")
            return None
        return self.GPS.get_corrected_timestamp()

    def stop(self):
        if self.GPS:
            self.GPS.stop()
