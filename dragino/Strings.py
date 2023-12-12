# used to ensure consistency by centralising names
# entries MUST match the config toml file entries - so, only 2 places to look

TTN="TTN"
OTAA="OTAA"
ABP="ABP"
AUTH_OTAA=OTAA
AUTH_ABP=ABP

AUTH_MODE="auth_mode"

LOG_FORMAT='%(asctime)s %(name)s - %(funcName)s - %(lineno)d - %(levelname)s - %(message)s'

CLASS_A="A"     # with a Pi Class A and B are almost the same (always listening)
CLASS_B="B"     # not supported
CLASS_C="C"

GPSD="GPSD"

DEVICE_CLASS="device_class"
FCNTUP="fCntUp"
FCNTDN="fCntDn"
RX1_DELAY="rx1_delay"
RX2_DELAY="rx2_delay"

JOIN_RETRIES="join_retries"
JOIN_TIMEOUT="join_timeout"

RX_WINDOW="rx_window" # duration
RX1_DR="rx1_DR"
RX2_DR="rx2_DR"
RX1_FREQUENCY="rx1_frequency"
RX1_FREQ_FIXED="rx1_freq_fixed"

RX2_FREQUENCY="rx2_frequency"
FREQUENCY_PLAN="frequency_plan"

#mapped to LORA_xxx_FREQS
CHANNEL_JOIN_FREQS="channelJoinFrequencies"
CHANNEL_TX_FREQS="channelTxFrequencies"
CHANNEL_RX1_FREQS="channelRX1Frequencies"


DUTY_CYCLE="duty_cycle"
DUTY_CYCLE_RANGE="duty_cycle_range"
DUTY_CYCLE_TABLE="duty_cycle_table"
MAX_DUTY_CYCLE="max_duty_cycle"

SF_RANGE="sf_range"
DEVADDR="devaddr"
VALID_DEVADDR="VALID_DEV_ADDR"
DEVEUI="deveui"
#NEWSKEY="newskey" spelling error
NWKSKEY="nwkskey"
APPSKEY="appskey"
APPEUI="appeui"
APPKEY="appkey"

MARGIN="margin"
GW_CNT="gw_Cnt"

MAX_POWER="max_power"
OUTPUT_POWER="output_power" # TX power

CH_MASK="ch_Mask"
CH_MASK_CTL="ch_Mask_Ctrl"
NB_TRANS="nb_Trans"
RX_CRC="rx_crc"

DATA_RATES="data_rates"
DATA_RATE="data_rate"
ADR_DATA_RATE="ADR_data_rate"
BANDWIDTHS="bandwidths"
MAX_CHANNELS="max_channels"
LORA_JOIN_FREQS="lora_join_freqs"
LORA_TX_FREQS="lora_tx_freqs"
LORA_RX1_FREQS="lora_rx1_freqs"

DOWNLINK_DWELL_TIME="downlink_dwell_time"
UPLINK_DWELL_TIME="uplink_dwell_time"
MAX_EIRP="maxEIRP"
SYNC_WORD="sync_word"
SERVER_TIME="server_time"
MAC_CACHE="mac_cache"
CFLIST="cfList"
MAX_DR_OFFSET="max_dr_offset"
MAX_DR_INDEX="max_dr_index"
DR_OFFSET_TABLE="DR_offset_table"

JOIN_RETRIES="join_retries"

# these settings are cached
# MAC settings which can be changed by a downlink msg containing MAC commands
MAC_SETTINGS=[
            FCNTUP,FCNTDN,RX1_DELAY,RX2_DELAY,RX1_DR, RX2_DR,RX1_FREQ_FIXED,
            RX1_FREQUENCY,RX2_FREQUENCY,DUTY_CYCLE,DATA_RATE
            ]

#TTN keys
KEY_SETTINGS=[DEVADDR,DEVEUI,NWKSKEY,APPSKEY,APPEUI,APPKEY]
