"""
MAChandler.py

Handles MAC commands sent by the server.

responses are placed in a list of tuples
when the responses are required to add to an uplink
the responses are converted to a bytearray

The array of responses is cleared after reading

All attributes are cached when the class is deleted
and reloaded when it is instantiated.

The initial attributes are set from the config file TTN section
when the class is instantiated and overwritten by the cached values.

To start over, delete the cache file before instantiating this class.

"""

import logging
import json
import toml
from .Strings import *
import random


# MAC commands have requests and answers
# the ID of the command is the same whether it is a REQ or ANS
class MCMD:
    LINK_CHECK_ANS=0x02
    LINK_CHECK_REQ=LINK_CHECK_ANS
    LINK_ADR_REQ=0x03
    DUTY_CYCLE_REQ=0x04
    RX_PARAM_SETUP_REQ=0x05
    DEV_STATUS_REQ= 0x06
    NEW_CHANNEL_REQ=0x07
    RX_TIMING_SETUP_REQ=0x08
    TX_PARAM_SETUP_REQ=0x09
    DL_CHANNEL_REQ=0x0A
    # 0x0B..0x0C RFU
    TIME_ANS=0x0D
    TIME_REQ=TIME_ANS
    # 0x0E..0x0F RFU
    # 0x10..0x1F reserved Class B commands
    # 0x20..0x2F reserved Class C commands
    # 0x30..0x7F RFU
    # 0x80..0xFF proprietry extensions
    """END - allows geany to collapse properly"""


DEFAULT_LOG_LEVEL=logging.DEBUG

class MAC_commands(object):

    def __init__(self,config, logging_level=DEFAULT_LOG_LEVEL):

        self.logger = logging.getLogger("MAChandler")
        self.logger.setLevel(logging_level)

        if config is None:
            self.logger.error("config is None")
            exit()
            
        self.config=config

        self.cache={} # TTN dynamic settings

        # jump table for MAC commands taken from spec 1.0.4
        # REQ are commands from the server requesting some info/changes
        # ANS are in response to MAC commands sent to the server
        self.commands = {
            MCMD.LINK_CHECK_ANS: self.link_check_ans,
            MCMD.LINK_ADR_REQ: self.link_adr_req,
            MCMD.DUTY_CYCLE_REQ: self.duty_cycle_req,
            MCMD.RX_PARAM_SETUP_REQ: self.rx_param_setup_req,
            MCMD.DEV_STATUS_REQ: self.dev_status_req,
            MCMD.NEW_CHANNEL_REQ: self.new_channel_req,
            MCMD.RX_TIMING_SETUP_REQ: self.rx_timing_setup_req,
            MCMD.TX_PARAM_SETUP_REQ: self.tx_param_setup_req,
            MCMD.DL_CHANNEL_REQ: self.dl_channel_req,
            # 0x0B..0x0C RFU
            MCMD.TIME_ANS: self.time_ans,
            # 0x0E..0x0F RFU
            # 0x10..0x1F reserved Class B commands
            # 0x20..0x2F reserved Class C commands
            # 0x30..0x7F RFU
            # 0x80..0xFF proprietry extensions
            }

        self.frequency_plan=self.config[TTN][FREQUENCY_PLAN]
        self.lastSNR=0
        self.setCacheDefaults()

        self.currentChannel=None  # changes with each transmission

        # initialise values from user config file
        # this gives the code a starting point on first run

                
        for k in MAC_SETTINGS:
            try: 
                self.logger.debug(f"Setting self.cache[{k}] to {self.config[TTN][k]}")
                self.cache[k]=self.config[TTN][k]
                
            except KeyError:
                self.logger.info(f"missing TTN section key {k} ignored")


        # get TTN network keys
        auth_mode=self.config[TTN][AUTH_MODE]
        
        for k in KEY_SETTINGS:
            try:
                self.logger.debug(f"Setting self.cache[{k}] to {self.config[TTN][auth_mode][k]}")
                self.cache[k]=self.config[TTN][auth_mode][k]
            except KeyError:
                self.logger.info(f"Missing {auth_mode} TTN key {k} ignored") 

        
        self.loadCache() # load any cached values

        # always reset these
        self.macReplies=bytearray()      # list of replies to MAC commands
        self.macCmds=None       # list of MAC commands in downlink
        self.macIndex=0         # pointer to next MAC cmd in macCmds

        # these values are tracked whenever a MAC linkCheckReq command is answered
        #
        # gw_margin is the signal strength above noise floor so min value gives us best
        # indication of decoder success
        # gw_cnt is the number of gateways which received our transmision. the linkCheckReq
        # must be issued a number of times because gateways in reach may not be listening

        self.gw_margin=0        # min is calculated
        self.gw_cnt=255         # max is calculated

        self.saveCache()        # update the cache
        
        self.logger.info("__init__ done")

    def setLastSNR(self,SNR):
        """
        used by status reply to server status req
        
        not cached because it can vary a lot
        """
        self.logger.info(f"last SNR value {SNR}")
        self.lastSNR=SNR

    '''
    getters and setters for cached values
    
    '''

    def getLinkCheckStatus(self):
        return (self.gw_margin,self.gw_cnt)

    def getRX1Delay(self):
        return self.cache[RX1_DELAY]

    def setRX1Delay(self,delay):
        """ passed in with JOIN_ACCEPT payload
        
        :param delay: seconds
        :return Nothing: no reply expected 
        """
        self.logger.info(f"set RX1 delay {delay}")
        self.cache[RX1_DELAY]=delay
        self.saveCache()
        
    def getDevAddr(self):
        try:
            return self.cache[DEVADDR]
        except:
            return [0x00,0x00,0x00,0x00]
    
    def setDevAddr(self,DevAddr):
        self.cache[DEVADDR]=DevAddr
        self.saveCache()
        
    def getNwkSKey(self):
        return self.cache[NWKSKEY]

    def setNwkSKey(self,key):
        self.cache[NWKSKEY]=key
        self.saveCache()
        
    def getAppSKey(self):
        return self.cache[APPSKEY]

    def setAppSKey(self,appskey):
        self.cache[APPSKEY]=appskey
        self.saveCache()
        
    def getAppKey(self):
        return self.cache[APPKEY]

    def getAppEui(self):
        return self.cache[APPEUI]

    def getDevEui(self):
        return self.cache[DEVEUI]

    def getFCntUp(self):
        return self.cache[FCNTUP]
        
    def setFCntUp(self,count):
        self.cache[FCNTUP]=count
        self.saveCache()

    def getJoinSettings(self):
        """
        When joining only the first three frequencies
        should be used
        
        max duty cycle is also selected
        
        :return (freq,sf,bw)
        """
        self.currentChannel=random.randint(0,len(self.cache[CHANNEL_JOIN_FREQS])-1)

        freq=self.cache[CHANNEL_JOIN_FREQS][self.currentChannel]

        self.cache[MAX_DUTY_CYCLE]=self.getMaxDutyCycle(freq)
        
        sf,bw=self.config[self.frequency_plan][DATA_RATES][self.cache[DATA_RATE]]

        self.logger.debug(f"using join settings: freq {freq} sf {sf} bw {bw}")
        return freq,sf,bw

    def getDataRate(self):
        return self.cache[DATA_RATE]

    def getLastSendSettings(self):
        """
        :return tuple: (freq,sf,bw)
        """
        return self.lastSendSettings
        
    def getSendSettings(self):
        """
        randomly choose a frequency (channel)
        
        once joined all frequencies are available for use
        
        Use current data rate
        
        :return (freq,sf,bw)
        """
        self.currentChannel=random.randint(0,len(self.cache[CHANNEL_TX_FREQS])-1)

        freq=self.cache[CHANNEL_TX_FREQS][self.currentChannel]
        self.cache[MAX_DUTY_CYCLE]=self.getMaxDutyCycle(freq)
          
        sf,bw=self.config[self.frequency_plan][DATA_RATES][self.cache[DATA_RATE]]
        
        self.logger.debug(f"using send settings: freq {freq} sf {sf} bw {bw}")
        return freq,sf,bw

    def getRX1Settings(self):
        """
        RX1 frequency varies with frequency plan

        :return (freq,sf,bw)
        """

        # RX1 frequency may have been fixed by MAC command
        if self.cache[RX1_FREQ_FIXED]:
            freq = self.cache[RX1_FREQUENCY]
            self.logger.debug(f"RX1 frequency has been fixed to {freq}")
        else:
            freq = self.cache[CHANNEL_RX1_FREQS][self.currentChannel]

        sf, bw = self.config[self.frequency_plan][DATA_RATES][self.cache[RX1_DR]]

        self.logger.debug(f"RX1 settings : freq {freq} sf {sf} bw {bw}")

        return freq, sf, bw

    def getRX2Settings(self):
        """
        RX2 is a fixed frequency,sf and bw
        
        :return (freq,sf,bw)
        """
        freq=self.cache[RX2_FREQUENCY]
        
        sf,bw=self.config[self.frequency_plan][DATA_RATES][self.cache[RX2_DR]]
        
        self.logger.debug(f"rx2 settings freq {freq} sf {sf} bw {bw}")
        return freq,sf,bw
        
    def getMaxDutyCycle(self,freq=None):
        """
        return the max duty cycle for a given frequency
        """
        if (self.currentChannel is None) or (freq is None):
            freq=self.cache[CHANNEL_TX_FREQS][0] #
            self.logger.error(f"Nothing has been transmitted. Using max duty cycle for {freq} instead")
                
        DC_table=self.config[self.frequency_plan][DUTY_CYCLE_TABLE]
        for (minFreq,maxFreq,dc) in DC_table:
            #self.cache[MAX_EIRP]= eirp
            if minFreq<=freq <=maxFreq:
                return dc
        self.logger.error(f"unable to locate max duty cycle for {freq}. Using 0.1 instead")
        return 0.1

    def getSfBw(self,drIndex):
        """
        gets the data rate for a given data rate index

        returns a tuple (sf,bw)

        The set_bw() function expects a value between 0 and 9

        """

        sf,bw=self.config[self.frequency_plan][DATA_RATES][drIndex]

        return (sf,bw)

    def get_bw_index(self,wanted):
        """

        the set_bw() function takes an index 0-9 check the value is valid

        :param wanted: one of [7.8, 10.4, 15.6, 20.8, 31.25, 41.7, 62.5, 125.0, 250.0, 500.0] kHz

        """
        return self.config[self.frequency_plan][BANDWIDTHS].index(wanted)

    def getFrequencyPlan(self):
        """
        get the frequency plan channel frequencies
        
        used internally
        
        """
        self.logger.info("loading frequency plan")
        try:
            
            self.logger.info(f"Frequency Plan is {self.frequency_plan}")

            self.channelDRRange = [(0, 7)] * self.config[self.frequency_plan][MAX_CHANNELS]
            #self.channelFrequencies=self.config[self.frequency_plan][LORA_FREQS]
            self.cache[CHANNEL_JOIN_FREQS]=self.config[self.frequency_plan][LORA_JOIN_FREQS]
            self.cache[CHANNEL_TX_FREQS] = self.config[self.frequency_plan][LORA_TX_FREQS]
            self.cache[CHANNEL_RX1_FREQS] = self.config[self.frequency_plan][LORA_RX1_FREQS]
            self.newChannelIndex=0
            
            self.logger.info("Frequency Plan loaded ok")

        except Exception as e:
            
            self.logger.error(f"error loading frequency plan. Check if it exists in the config toml file. {e}")

    def setDLsettings(self,settings):
        """ 
        passed in with JOIN_ACCEPT payload       
        
        :param settings: upper byte RX1 DR offset, lower RX2 DR
        :return nothing: JOIN_ACCEPT does not expect a reply
        """
        rx1_dr_offset=(settings & 0x70)>>4
        
        dr_table_row=self.config[self.frequency_plan][DR_OFFSET_TABLE][self.cache[DATA_RATE]]
        rx1_dr=dr_table_row[rx1_dr_offset]
        
        self.cache[RX1_DR]=rx1_dr
        self.cache[RX2_DR]=settings & 0x0F
        self.saveCache()
        
        self.logger.info(f"DL settings rx1_dr_offset{rx1_dr_offset} rx1_DR {rx1_dr} rx2_DR {settings & 0x0F}")
        
    def _computeFreq(self,a):
        """
        :param  a: byte array of 3 octets 
        :return f: frequency in xxx.y mHz  format
        """
        freq=(a[2] << 16 ) + (a[1] << 8) + a[0] * 100
        # frequency is like 868100000 but we want 868.1
        return freq/1000000    
        
    def handleCFList(self,delay,cflist):
        """
            upto 16 bytes
            5 channel frequencies in groups of 3 bytes per frequency
            plus one byte 0 passed in with JOIN_ACCEPT payload
        
        :param cflist: 5 channel frequencies packed in 3 bytes LSB first     
        """
        
        self.logger.info("processing cfList from JOIN_ACCEPT")
        
        if cflist[-1:]!=0:
            self.logger.info("cfList type is non-zero")
        
        ch=4;
        for entry in range(5):
            # get each slice
            i=entry*3
            self.lora_freqs[ch]=self._computeFreq(cflist[i:i+3])
            ch+=1
        
    def setCacheDefaults(self):
        """
        default settings
        
        """
        self.logger.info("Setting default MAC values using user config values")
        
        self.cache[DATA_RATE]=self.config[TTN][DATA_RATE]
        self.cache[CHANNEL_JOIN_FREQS] = self.config[self.frequency_plan][LORA_JOIN_FREQS]
        self.cache[CHANNEL_TX_FREQS] = self.config[self.frequency_plan][LORA_TX_FREQS]
        self.cache[CHANNEL_RX1_FREQS] = self.config[self.frequency_plan][LORA_RX1_FREQS]
        self.cache[OUTPUT_POWER]=self.config[TTN][OUTPUT_POWER]
        self.cache[MAX_POWER]=self.config[TTN][MAX_POWER]
                
        #self.channelDRrange = [(0,7)] * self.config[self.frequency_plan][MAX_CHANNELS]  # all disabled

        # extract freqs from frequency plan

        self.getFrequencyPlan()

        # the following attributes can be changed by MAC commands
        # not all are cached
        # these are listed in groups according to the MAC command
        # which changes the value
        # they are also over written from the user config and MAC cache
        

        # link ADR req
        # for a in [CH_MASK,CH_MASK_CTL,NB_TRANS]:
        #    self.cache[a]=0

        # Duty Cycle req - percentage airtime allowed
        # duty cycle depends on frequency but is mostly
        # 1% in EU868
        self.cache[DUTY_CYCLE]=1  

        # RXParamSetup
        self.cache[RX1_DR]=self.config[TTN][RX1_DR]
        self.cache[RX2_DR]=self.config[TTN][RX2_DR]

        # TX and RX1 frequencies change, RX2 is constant (in UK)
        # RX1 frequency can be set by MAC
        self.cache[RX1_FREQ_FIXED]=False
        self.cache[RX2_FREQUENCY]=self.config[TTN][RX2_FREQUENCY]
        self.cache[RX1_DELAY]=self.config[TTN][RX1_DELAY]
        self.cache[RX2_DELAY]=self.config[TTN][RX2_DELAY]
        
        # with OTAA some of these are set after joining
        # and cached so that a JOIN isn't needed every time
        auth_mode=self.config[TTN][AUTH_MODE]
        
        self.cache[APPKEY]=self.config[TTN][auth_mode][APPKEY]
        self.cache[APPEUI]=self.config[TTN][auth_mode][APPEUI]
        self.cache[DEVEUI]=self.config[TTN][auth_mode][DEVEUI]
                    
        if self.config[TTN][AUTH_MODE]==OTAA:
            # NWKSKEY and APPSKEY are set after joining
            self.cache[DEVADDR]=[0x00,0x00,0x00,0x00]
            self.cache[APPSKEY]=[0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00]
            self.cache[NWKSKEY]=[0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00]

        else:
            # ABP settings
            self.cache[DEVADDR]=self.config[TTN][ABP][DEVADDR]
            self.cache[APPSKEY]=self.config[TTN][ABP][APPSKEY]
            self.cache[NWKSKEY]=self.config[TTN][ABP][NWKSKEY]

        # frame counts - will be reset on OTAA joining
        self.cache[FCNTUP]=self.config[TTN][FCNTUP]
        self.cache[FCNTDN]=self.config[TTN][FCNTDN]
             
        self.logger.info("MAC default settings finished")
        
        # do not call saveCache() - loadCache() will do that if
        # the cache file doesn't exist
        
    def saveCache(self):
        """
        MAC commands received from TTN alter device behaviour
        """
        try:
            self.logger.info("Saving MAC settings")

            with open(self.config[TTN][MAC_CACHE], "w") as f:
                json.dump(self.cache, f)
            
        except Exception as e:
            self.logger.error(f"Saving MAC settings failed {e}.")
    
    def incrementFcntUp(self):
        """
        increments the FcntUp and save to cache
        """
        self.cache[FCNTUP]+=1
        self.saveCache()
        
    def checkFcntDn(self,fcntdn):
        """
        fcntdn should be incrementing
        """
        prev=self.cache[FCNTDN]
        
        if fcntdn<=prev:
            self.logger.warn("received downlink FCntDn < or = previous")
            return
        

        self.cache[FCNTDN]=fcntdn
        self.saveCache()
            
    def loadCache(self):
        """
        load mac parameters (if saved)
        
        """

        self.logger.info("Loading MAC settings")


        settings={}

        try:           
            with open(self.config[TTN][MAC_CACHE], "r") as f:
                settings = json.load(f)

            if not settings:
                self.logger.warning("cached MAC settings is empty. Could be first run?")
                return

            self.cache=settings
    
            self.logger.info("cached settings loaded ok")
            
        except Exception as e:
            self.logger.error(f"cached settings load failed {e}. Saving current defaults")
            self.saveCache()

    def getFOpts(self):
        """
        these are the MAC replies. The spec says the server can send multiple
        commands in a packet.
        
        The replies are cleared when this method is called otherwise
        they would be sent to TTN with every uplink
        
        :param: None
        :return: (Fopts,FoptsLen)
        :rtype: tuple
        """
        FOpts=self.macReplies # should this be reversed?
        FOptsLen=len(FOpts)

        self.logger.info(f"check for FOpts to attach to uplink len={FOptsLen} FOpts={FOpts}")

        self.macReplies=bytearray() # clear them as we don't want to send with every messages

        if FOptsLen==0:
            self.logger.info("no FOpts")
            return [],0
            
        if FOptsLen>0 and FOptsLen<=16:
            return (FOpts,FOptsLen)

        self.logger.warning(f"FOpts len={FOptsLen} exceeds 16 bytes={FOpts}")
        return [],0

####################################################
#
# here are the MAC command handlers
#
# taken from the V1.0.4 spec
#
####################################################

    def handleCommand(self, macPayload):
        """
        these are commands originated from the server

        They are only executed if FPort==0

        MAC conmands are acknowledged by sending an uplink repeating
        the command CID

        This method is called if a message includes a MAC payload
        
        :param macPayload: a MAC payload object
        """
        self.logger.debug("checking MAC payload for MAC commands")


        FCtrl=macPayload.get_fhdr().get_fctrl()
        FOptsLen=FCtrl & 0x0F

        FCnt=macPayload.get_fhdr().get_fcnt() # frame downlink frame counter
        self.logger.debug(f"received frame FCnt={FCnt} FCntDn={self.cache[FCNTDN]}")
  
        self.cache[FCNTDN]=FCnt
    
        FOpts=macPayload.get_fhdr().get_fopts()
        FPort=macPayload.get_fport()
        FRMpayload=macPayload.get_frm_payload()
        self.logger.debug(f"FCtrl={FCtrl} FCnt={FCnt} FOpts={FOpts} FoptsLen={FOptsLen} FPort={FPort}")

        # mac commands may contain several commands
        # all need replying to in the order sent
        self.macReplies=bytearray()

        if FOptsLen==0:
            # no MAC commands
            self.logger.debug("No FOpts to process")
            return

        # MAC commands can appear in FOpts field or FRMpayload but not both
        
        #if FPort == 0:
            # MAC commands only and in FRMpayload
        #    self.logger.debug(f"MAC commands in FRMpayload")
            #FOpts=FRMpayload
        #else:
            # commands are in the FOpts field
        #    self.logger.debug(f"MAC commands in FOpts field {FOpts}")


        # process the MAC commands - there may be multiple commands
        # all may need answering

        self.processFopts(FOpts)

    def processFopts(self,FOpts):
        """
        can be called directly if downlink message does not include a FRM payload
        
        :param FOpts: array of MAC commands
        
        """
        self.logger.info(f"handling downlink FOpts {FOpts}")
        self.macIndex=0
        self.macCmds=FOpts
        
        while self.macIndex<len(self.macCmds):
            CID=self.macCmds[self.macIndex]
            # called functions add to self.macReplies
            self.logger.debug(f"Calling MAC cmd with CID {CID}")
            try:
                func = self.commands[CID]
                func()
            except KeyError:
                self.logger.error(f"invalid MAC command CID {CID}. Aborting MAC handling")
                break
                
        # update any changes
        self.saveCache()

    def link_check_req(self):
        """
        adds a link check request to the macReplies list
        this will be sent with the next uplink
        
        The server will send a LINK_CHECK_ANS.
        """
        self.logger.debug("LINK_CHECK_REQ")
        self.macReplies+=bytearray([MCMD.LINK_CHECK_REQ])

    def link_check_ans(self):
        """
        The server sends this to acknowledge us sending a LinkCheckReq
        
        Recieved payload will be 2 bytes [Margin][GwCnt]
        
        GwCnt is number of gateways which received the transmission from us
        Margin is the the demod margin (db) range 0..254 (255 reserved)
        
        no response needed
        """
        self.logger.debug("LINK_CHECK_ANS")
        # values can be retrieved with getLinkCheckStatus()
        self.gw_margin=min(self.gw_margin,self.macCmds[self.macIndex+1])
        self.gw_cnt=max(self.gw_cnt,self.macCmds[self.macIndex+2])
        self.logger.debug(f"link check ans margin {self.gw_margin} GwCnt {self.gw_cnt}")
        self.macIndex+=3
        
    def link_adr_req(self):
        """
        Server is asking us to do a data rate adaption
        payload (bytes) is [DR & txPower:1][chMask:2][redundancy:1]

        ChMask determines the channels usable for uplink access

        data_rate & power [DR: 7..4, Power: 3..0] Region Specific

        redundancy rfu:7, ChMaskCntl:6..4 , NbTrans:3..0

        return status byte: RFU:7..3, PowerAck:2, DRAck: 1, ChMaskAck:0
        """
        self.logger.debug("LINK_ADR_REQ")
        self.cache[RX1_DR]=self.macCmds[self.macIndex+1] & 0xF0 >> 4
        self.cache[OUTPUT_POWER]=self.macCmds[self.macIndex+1] & 0x0F
        self.cache[CH_MASK]=self.macCmds[self.macIndex+2] << 8 & self.macCmds[self.macIndex+3]
        self.cache[CH_MASK_CTL]=self.macCmds[self.macIndex+4] & 0x0e >> 4
        self.cache[NB_TRANS]=self.macCmds[self.macIndex+4] & 0x0F
        self.macReplies+=bytearray([MCMD.LINK_ADR_REQ])
        self.macIndex+=5

    def duty_cycle_req(self):
        """
        Change the duty cycle

        1 byte [RFU: 7..4][MaxDutyCycle: 3..0]

        value not used - we are using the duty_cycle_range in the frequency plan
        section of the config file

        """
        self.logger.debug("DUTY_CYCLE_REQ")
        self.cache[MAX_DUTY_CYCLE]=self.macCmds[self.macIndex+1] & 0x0F
        self.macReplies+=bytearray([MCMD.DUTY_CYCLE_REQ])
        self.macIndex+=2

    def rx_param_setup_req(self):
        """
        Setup RX2 parameters

        payload=[DLSettings:1] [Frequency:3]:
        
        DLsettings [RFU:7,RX1DROffset:6..4,RX2DataRate:3..0]

        reply is 1 byte with bit encoding
        RFU:7..3,RX1DROffsetAck:2, RX2DataRateACK:2,ChannelACK:0
        """
        self.logger.debug("RX_PARAM_SETUP_REQ")

        DLSettings=self.macCmds[self.macIndex+1]

        # TODO only if all are valid otherwise no change
        reply=0x00
        
        rx1_dr_offset=(DLSettings & 0xE0) >> 4
        if 0<=rx1_dr_offset<=5:
            reply=reply or 0x01
            
        rx2_dr_index=(DLSettings & 0x0F)
        if 0<=rx2_dr_index<=8:
            reply=reply or 0x02
            
        freq=self._computeFreq(self.macCmds[self.macIndex+2:self.macIndex+4])
        
        if freq in self.cache[CHANNEL_RX1_FREQS][self.currentChannel]:
            reply=reply or 0x04
            
        if reply==0x07:
            self.cache[RX1_DR]+=rx1_dr_offset
            self.cache[RX2_DR]=rx2_dr_index
            self.cache[RX2_FREQUENCY]=freq
        
        # Channel ACK       0=unusable, 1 ok
        # RX2DataRateAck    0=unknown data rate, 1 ok
        # RX1DROffsetACK    0=not in allowed ranbge, 1 ok
        self.macReplies+=bytearray([MCMD.RX_PARAM_SETUP_REQ,0x07])
        self.macIndex+=5

    def dev_status_req(self):
        """
        Server is asking for device status

        return 2 bytes [battery][RadioStatus]

        Battery
        0 = connected to external power source
        1..254 battery level
        255 - not able to measure

        Radio Status from last dev_status_req command
        bits 5..0 SNR 6 bit signed int

        """
        self.logger.info(f"DEV_STATUS_REQ - returns (0,{int(self.lastSNR)})")
        self.macReplies+=bytearray([MCMD.DEV_STATUS_REQ,0,int(self.lastSNR)])
        self.macIndex+=1

    def new_channel_req(self):
        """
        modify a channel

        payload [ChIndex:0][Frequency:1..3][DRRange:4]

        TODO split DRRange

        reply 1 byte encoded RFU:7..2, DataRateOk: 1, ChannelFreqOk 0
        """
        self.logger.debug("NEW_CHANNEL_REQ")

        chIndex = self.macCmds[self.macIndex+1]
        newFreq=self._computeFreq(self.macCmds[self.macIndex+2:self.macIndex+5])
        
        DRRange = self.macCmds[self.macIndex+5] # uplink data rate range (max,min)
        
        maxDR=(DRRange &0xF0) >>4
        minDR=(DRRange &0x0F)
        
        # TODO - check newFreq is possible first
        # needs to know region parameters
        minFreq=min(self.cache[CHANNEL_TX_FREQS])
        maxFreq=max(self.cache[CHANNEL_TX_FREQS])

        if not (minFreq<=newFreq<=maxFreq):
            self.logger.info(f"new freq {newFreq} not in range min {minFreq} - {maxFreq}")
            self.macReplies+=bytearray([MCMD.NEW_CHANNEL_REQ,0x02])
  
        else:
            self.cache[CHANNEL_TX_FREQS][chIndex]=newFreq
            self.channelDRRange[chIndex] = (minDR,maxDR)
            
            self.logger.info(f"NewChannelReq chIndex {chIndex} freq {newFreq} maxDR {maxDR} minDR {minDR}")

            # answer - assume all ok
            self.macReplies+=bytearray([MCMD.NEW_CHANNEL_REQ,0x03])
        
        self.macIndex+=6

    def rx_timing_setup_req(self):
        """
        payload is 1 byte RX1 delay encoded in bits3..0
        """
        self.logger.debug("RX_TIMING_SETUP_REQ")

        rx1_delay=self.macCmds[self.macIndex+1] & 0x0f # seconds
        if rx1_delay == 0:
            rx1_delay = 1
            
        self.cache[RX1_DELAY]=rx1_delay

        self.logger.info(f"rx timing setup RX1 delay={rx1_delay}")
        
        self.macReplies+=bytearray([MCMD.RX_TIMING_SETUP_REQ])
        self.macIndex+=2

    def tx_param_setup_req(self):
        """
        payload 1 byte
        [RFU:7..6][DownlinkDwellTime:5][UplinkDwellTime:4][maxEIRP:3..0]

        DwellTimes: 0= no limit, 1=400ms
        
        Currently the values are stored and acknowledged but not used
        """
        self.logger.debug("TX_PARAM_SETUP_REQ")
        dldt=self.macCmds[self.macIndex+1] & 0x20 >> 5
        uldt=self.macCmds[self.macIndex+1] & 0x10 >> 4
        maxEirp=self.macCmds[self.macIndex+1] & 0x0F
        
        self.cache[DOWNLINK_DWELL_TIME]=dldt
        self.cache[UPLINK_DWELL_TIME]=uldt
        self.cache[MAX_EIRP]=maxEirp
        
        self.logger.info(f"tx param setup DL dwell {dldt} UL dwell {uldt} maxEIRP {maxEirp}")
        
        self.macReplies+=bytearray([MCMD.TX_PARAM_SETUP_REQ])
        self.macIndex += 2

    def dl_channel_req(self):
        """
        only EU863-870 & CN779-787

        payload 4 bytes
        [ChIndex:1][Freq:3]

        reply 1 byte bit encoded
        [RFU 7:2][Uplink Freq Exists 1][channel freq ok 0]

        """
        self.logger.debug("DL_CHANNEL_REQ")
        chIndex = self.macCmds[self.macIndex+1]
        newFreq =self._computeFreq(self.macCmds[self.macIndex+2:self.macIndex+5])
        #self.channelFrequencies[ChIndex] = newFreq
        self.cache[CHANNEL_RX1_FREQS][chIndex]=newFreq
        self.cache[RX1_FREQ_FIXED]=True
        self.cache[RX1_FREQUENCY]=newFreq

        self.logger.info(f"DL channel req ChIndex {chIndex} newFreq {newFreq}")

        # answer - 
        # assume Uplink Frequency exists and channel freq ok
        self.macReplies+=bytearray([MCMD.DL_CHANNEL_REQ,0x03])
        self.macIndex += 5

    def time_req(self):
        """
        prompt the server for a TIME_ANS
        """
        self.logger.debug("TIME_REQ")
        self.macReplies+=bytearray([MCMD.TIME_REQ])

    def time_ans(self):
        """
        introduced in 1.0.3

        It is the time at the end of the uplink transmission requesting it.

        payload 5 bytes
        [seconds since epoch:0..3][fractional seconds:4]

        Fractional seconds are 1/256 s increments

        Received as a Class A downlink

        """
        self.logger.debug("TIME_ANS")
        seconds=self.macCmds[self.macIndex+1:self.macIndex+5]
        fraction=self.macCmds[self.macIndex+5] / 256


        self.logger.info(f"server time was {seconds}.{fraction}")

        # to use this the caller needs to track time of sending
        # warning, using the returned values can be a problem
        # we can determin the time the server received the request
        # but it will be hard to tell how long it takes to receive
        # the information back hence there will be an error. However,
        # if the end device time is massively different then it should be 
        # corrected but the Dragino HAT has a GPS and can be time synced to that
        # use the server time at your peril

        # this is a response from the server when we send a time_req.
        # Does not require an ACK
        self.macIndex+=6
