"""
License: see license_gpl-3.0.txt
"""

from solarmqtt import SolarMQTT, IOBrokerMQTT
from epever import EPEVER
from adafruit_simplemath import constrain
import adafruit_logging as logging
from MQTTHandler import MQTTHandler
import ipaddress
import adafruit_ntp

import wifi
import socketpool
import board
import os
import sys
import busio
import digitalio
import time
import binascii
import asyncio
import json
import gc

LED = board.LED


UART0_TX = eval(f"board.{os.getenv('UART0_TX')}")
UART0_RX = eval(f"board.{os.getenv('UART0_RX')}")
UART1_TX = eval(f"board.{os.getenv('UART1_TX')}")
UART1_RX = eval(f"board.{os.getenv('UART1_RX')}")
#UART2_TX = eval(f"board.{os.getenv('UART2_TX')}")
#UART2_RX = eval(f"board.{os.getenv('UART2_RX')}")

log = logging.getLogger('SolarPICO')        
log.setLevel(os.getenv('LOGLEVEL'))
log_handlers = os.getenv('LOGGER_HANDLERS').split(',')

epever_devices = []

log.info(os.getenv('SOLAR_PICO_VERSION'))

if os.getenv('MODBUS_UART') == 0:
    uart = busio.UART(UART0_TX, UART0_RX, baudrate=os.getenv('MODBUS_BAUD'))
    log.info("UART0 connected")
elif os.getenv('MODBUS_UART') == 1:
    uart = busio.UART(UART1_TX, UART1_RX, baudrate=os.getenv('MODBUS_BAUD'))
    log.info("UART1 connected")
else:
    msg = "UART not correctly configured"
    log.error(msg)
    sys.exit(msg)
    
ids = os.getenv('EPEVER_DEVICE_IDS')
ids = [int(i) for i in ids.split(',')]
log.info(f"EPEVER devices: {ids}")

names = os.getenv('EPEVER_TOPIC_KEY').split(',')
#soyo = SoyoSource(soyo_uart)

log.info("Connecting to WiFi ...")
wifi.radio.hostname = os.getenv('PICO_WIFI_HOSTNAME')
wifi.radio.connect(os.getenv('PICO_WIFI_SSID'), os.getenv('PICO_WIFI_PASSWORD'))

log.info("SolarPICO connected")
pool = socketpool.SocketPool(wifi.radio)
mac = ":".join([ f"{i:02x}" for i in wifi.radio.mac_address]).upper()
log.info(f"MAC:{mac}")
log.info(f"IP-Address: {wifi.radio.ipv4_address}")

log.info(f"RTC-Sync enabled: {bool(os.getenv('EPEVER_SYNC_RTC_ENABLE'))}")
# get my IOBrokerMQTT object

baseMQTT=SolarMQTT(wifi=wifi, logger=log)
mqtt = IOBrokerMQTT(wifi=wifi, logger=log)


#gc.collect()
#print(f“Free memory at code point”)

# initialize EPEVER devices
print ("-S---------")
obj = MQTTHandler(mqtt=baseMQTT, topic=os.getenv('MQTT_PREFIX'))
for i in range(len(ids)):
    epever = EPEVER(uart=uart, logger=None, handler=obj, slaveID=i, name=names[i], pool=pool, demo=bool(os.getenv('EPEVER_DEMO')))
    epever_devices.append(epever)            
    time.sleep(1)
print ("-E---------")

class Interval:
    """Simple class to hold an interval value and an error code. Use .value to to read or write."""
    
    def __init__(self, initial_interval, min=None, max=None):
        if min != None and max != None:
            self.value = constrain(self.value, min, max)
        self.value = float(initial_interval / 1000)

async def TaskHeartBeat(interval):
    """ Simple Heartbeat-Signal """
    while True:
        with digitalio.DigitalInOut(LED) as led:
            led.switch_to_output(value=False)
            log.info(f">>>> HEART-BEAT <<<< ")
            led.value = True
            time.sleep(0.25)
            led.value = False
            time.sleep(0.15)
        gc.collect()
        log.info(f"######### MEMORY : {gc.mem_free()} ###########")
        await asyncio.sleep(interval.value)

async def TaskEPEVERSyncRTC(devices, interval):
    """ Asynchronous task to sync internen RTC in EPEVER devices """
    tz_offset = (0 if os.getenv('EPEVER_SYNC_TZ_OFFSET') is None else os.getenv('EPEVER_SYNC_TZ_OFFSET'))
    while True:
        for epever in devices:
            epever_sub_topic = epever.getName() + "/"
            reg = "9013"
            fc = "03"
            log.info(f"""
************************************************************
SyncRTC via register {reg} --  every {interval.value}sec
************************************************************
""")
            raw, converted = epever.read(fc, int(hex(int(reg,16)),16))
            if converted != None and raw != None:
                rc = mqtt.publish(epever_sub_topic, converted)
                epever_dt = converted[fc]["value"]
                log.info(f"RTC time from {epever.getName()} : {epever_dt}")
                
            pico_dt = adafruit_ntp.NTP(pool, tz_offset=tz_offset)
            log.info(f"PICO time from {wifi.radio.hostname} : {pico_dt.datetime}")


            await asyncio.sleep(interval.value)


async def TaskEPEVER(devices, interval):
    """ Asynchronous task to read EPEVER MPPT charger - only READ """
    #epever_sub_topics = os.getenv("EPEVER_TOPIC_KEY").split(",")
    while True:
        for epever in devices:
            epever_sub_topic = epever.getName() + "/"
            registers = sorted(epever.getFunctionCodeList())
            for fc in registers:
                for reg in sorted(epever.getRegisterList(fc)):
                    raw, converted = epever.read(fc, int(hex(int(reg,16)),16))
                    rc = mqtt.publish(epever_sub_topic, converted)
                    rc = mqtt.generateStatistic(epever_sub_topic, converted)                
                    await asyncio.sleep(interval.value)
       
async def main():
    epever_interval =  Interval(os.getenv('EPEVER_INTERVAL'))                   # value in milliseconds
    epever_sync_interval =  Interval(os.getenv('EPEVER_SYNC_INTERVAL')*1000)    # value in seconds
    epever_enable_sync = bool(os.getenv('EPEVER_SYNC_RTC_ENABLE'))              # True/False
    hb_interval = Interval(os.getenv('HEARTBEAT_INTERVAL'))                     # value in milliseconds
    
    epever_task = asyncio.create_task(TaskEPEVER(epever_devices,epever_interval))
    hb_task = asyncio.create_task(TaskHeartBeat(hb_interval))
    if epever_enable_sync:
        log.info("**ENABLE** Epever RTC synchronisation....")
        epever_sync_task = asyncio.create_task(TaskEPEVERSyncRTC(epever_devices,epever_sync_interval))
        await asyncio.gather(epever_task, hb_task, epever_sync_task)
    else:
        log.info("--DISABLE-- Epever RTC synchronisation....")
        await asyncio.gather(epever_task, hb_task)
    

for i in range (5):
    with digitalio.DigitalInOut(LED) as led:
        led.switch_to_output(value=False)    
        led.value = True
        time.sleep(0.15)
        led.value = False
        time.sleep(0.10)        

asyncio.run(main())
