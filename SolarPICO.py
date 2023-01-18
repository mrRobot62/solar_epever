"""
License: see license_gpl-3.0.txt
"""

from solarmqtt import SolarMQTT, IOBrokerMQTT
from epever import EPEVER
import adafruit_logging as logging
import ipaddress

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
LED = board.LED


UART0_TX = eval(f"board.{os.getenv('UART0_TX')}")
UART0_RX = eval(f"board.{os.getenv('UART0_RX')}")
UART1_TX = eval(f"board.{os.getenv('UART1_TX')}")
UART1_RX = eval(f"board.{os.getenv('UART1_RX')}")
#UART2_TX = eval(f"board.{os.getenv('UART2_TX')}")
#UART2_RX = eval(f"board.{os.getenv('UART2_RX')}")

log = logging.getLogger('SolarPICO')        
log.setLevel(os.getenv('LOGLEVEL'))
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


# get my IOBrokerMQTT object
mqtt = IOBrokerMQTT(SolarMQTT(wifi))

# initialize EPEVER devices
print ("-S---------")
for i in range(len(ids)):
    epever_devices.append(EPEVER(uart=uart, slaveID=ids[i], name=names[i], demo=False, pool=pool))
    time.sleep(1)
print ("-E---------")


class ErrorObj:
    """ Simple class to hold an error code and an error interval"""
    
    def __init__(self, idle_interval, error_interval):
        self._value = self._idle_interval = self.value(idle_interval, 1000)
        self._error_interval = self.error_interval(error_interval, 1000)
        self._error = 1
    
    def value(self, interval=None, scale=1):
        if interval != None:
            self._value = float(interval / scale)
        return self._value
    
    def error_interval(self, interval=None, scale=1):
        if interval != None:
            self._error_interval = float(interval / scale)
        return self._error_interval
    
    def idle_interval(self, interval=None, scale=1):
        if interval != None:
            self._idle_interval = float(interval / scale)
        return self._idle_interval
    
    def errID(self, error=None):
        """ getter/setter error code """
        if error != None:
            self._error = (error if error > 1 else 1)
        return self._error
        
class Interval:
    """Simple class to hold an interval value and an error code. Use .value to to read or write."""
    
    def __init__(self, initial_interval):
        self.value = float(initial_interval / 1000)

async def TaskHeartBeat(interval, error):
    """ Simple Heartbeat-Signal """
    while True:
        with digitalio.DigitalInOut(LED) as led:
            led.switch_to_output(value=False)
#            count = error.errID()
#            log.info(f">>>> HEART-BEAT <<<< {error.value()}/{count}")
            log.info(f">>>> HEART-BEAT <<<< ")
#            if count > 1:
#                error.value(error.error_interval())
#            else:
#                error.value(error.idle_interval())
#                count=1
#            for i in range(count):
            led.value = True
            time.sleep(0.25)
            led.value = False
            time.sleep(0.15)
       
        await asyncio.sleep(interval.value)

async def TaskEPEVERSyncRTC(devices, interval, error):
    """ Asynchronous task to sync internen RTC in EPEVER devices """
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
            rc = mqtt.publish(epever_sub_topic, converted)
            
            await asyncio.sleep(interval.value)


async def TaskEPEVER(devices, interval, error):
    """ Asynchronous task to read EPEVER MPPT charger - only READ """
    #epever_sub_topics = os.getenv("EPEVER_TOPIC_KEY").split(",")
    while True:
        for epever in devices:
            epever_sub_topic = epever.getName() + "/"
            registers = sorted(epever.getFunctionCodeList())
            for fc in registers:
                log.info (f"""
-----------------------------------
{epever.name} - FCode '{fc}'
-----------------------------------

""")
                for reg in sorted(epever.getRegisterList(fc)):
                    log.info (f"""
    -----------------------------------
    {epever.name} --- Register '{reg}'
    -----------------------------------
""")
                    raw, converted = epever.read(fc, int(hex(int(reg,16)),16))
#                    if raw is None or converted is None:
#                        error.errID(os.getenv('HEARTBEAT_ERROR_MODBUS'))
#                    else:
#                        error.errID(0)	# no error
                        
                    rc = mqtt.publish(epever_sub_topic, converted)
                    rc = mqtt.generateStatistic(epever_sub_topic, converted)                
                    await asyncio.sleep(interval.value)
       
async def main():
    errObj = ErrorObj(idle_interval=os.getenv('HEARTBEAT_IDLE_INTERVAL'), error_interval=os.getenv('HEARTBEAT_ERROR_INTERVAL'))
    epever_interval =  Interval(os.getenv('EPEVER_INTERVAL'))
    epever_sync_interval =  Interval(os.getenv('EPEVER_SYNC_RTC_DELTA')*1000)
    epever_enable_sync = os.getenv('EPEVER_SYNC_RTC_ENABLE')
    hb_interval = Interval(os.getenv('HEARTBEAT_INTERVAL'))
    err_interval = Interval(30000)
    
    epever_task = asyncio.create_task(TaskEPEVER(epever_devices,epever_interval,errObj))
    hb_task = asyncio.create_task(TaskHeartBeat(hb_interval,errObj))
    if epever_enable_sync:
        log.info("ENABLE Epever RTC synchronisation....")
        epever_sync_task = asyncio.create_task(TaskEPEVERSyncRTC(epever_devices,epever_sync_interval,errObj))
        await asyncio.gather(epever_task, hb_task, epever_sync_task)
    else:
        await asyncio.gather(epever_task, hb_task)
    



    
for i in range (5):
    with digitalio.DigitalInOut(LED) as led:
        led.switch_to_output(value=False)    
        led.value = True
        time.sleep(0.15)
        led.value = False
        time.sleep(0.10)        

asyncio.run(main())




