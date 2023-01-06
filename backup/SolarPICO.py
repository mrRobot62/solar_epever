from dalybms import DalyBMS
from solarmqtt import SolarMQTT
from soyosourcegtn import SoyoSource
from epever import EPEVER
import adafruit_logging as logging

import wifi
import board
import os
import busio
import digitalio
import time
import binascii
import asyncio

#TX = board.GP0
#RX = board.GP1

LED = board.LED

UART0_TX = eval(f"board.{os.getenv('UART0_TX')}")
UART0_RX = eval(f"board.{os.getenv('UART0_RX')}")

UART1_TX = eval(f"board.{os.getenv('UART1_TX')}")
UART1_RX = eval(f"board.{os.getenv('UART1_RX')}")

#wifi.radio.connect(os.getenv('CIRCUITPY_WIFI_SSID'), os.getenv('CIRCUITPY_WIFI_PASSWORD'))
#mqtt = SolarMQTT(wifi)

uart0 = busio.UART(UART0_TX, UART0_RX, baudrate=9600)
uart1 = busio.UART(UART1_TX, UART1_RX, baudrate=115200)

bms = DalyBMS(uart0)
epever = EPEVER(uart1)

#soyo = SoyoSource(soyo_uart)

log = logging.getLogger('EPEVER')        
log.setLevel(os.getenv('EPEVER_LOGLEVEL'))


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
            self._error = (error if error > 0 else 1)
        return self._error
        
class Interval:
    """Simple class to hold an interval value and an error code. Use .value to to read or write."""
    
    def __init__(self, initial_interval):
        self.value = float(initial_interval / 1000)
        
async def TaskWriteLimiter(obj, interval, error):
    while True:
        await asyncio.sleep(interval.value)

        
async def TaskReadLimiter(obj, interval, error):
    """ """
    while True:
        print (f"\n-- SOYO READ -------------------------")
        data = obj.readSOYO()
        print (f"SOYO-DATA {data}")
        result = obj.convertData(data)
        print(f"Data from SOYO '{result}'")
        await asyncio.sleep(interval.value)

async def TaskBMS(bms, interval, error):
    """ Asynchronous worker for DalyBMS. Read out register, write data via MQTT """ 
    while True:
        for register in sorted(bms.getRegisterList()):
            print (f"\n-- 0x{register} ------------------------")
            print(f"==> Send command '{bms.getRegisterCMD(register)}'")
            nbytes = bms.writeBMS(bms.getRegisterCMD(register))
            time.sleep(0.1)
    #        #data = readBMSRaw(nbytes=0, cmd=cmd)
            data = bms.readBMSRaw(cmd=register)
            print(f"<== BMS data received '{binascii.hexlify(data)}'")
            result = bms.convertData(data)
            print(f"Data from BMS '{result}'")
            await asyncio.sleep(interval.value())

async def TaskHeartBeat(interval, error):
    """ Simple Heartbeat-Signal """
    while True:
        with digitalio.DigitalInOut(LED) as led:
            led.switch_to_output(value=False)
            count = error.errID()
            print (f">>>> HEART-BEAT <<<< {error.value()}/{count}")
            if count > 1:
                error.value(error.error_interval())
            else:
                error.value(error.idle_interval())
                count=1
            for i in range(count):
                led.value = True
                time.sleep(0.25)
                led.value = False
                time.sleep(0.15)
       
        await asyncio.sleep(interval.value)

async def TaskEPEVER(epever, interval, error):
    """ Asynchronous task to read EPEVER MPPT charger - only READ """

    while True:
        for fc in sorted(epever.getFunctionCodeList()):
            print (f">>>>>>>>> FCode '{fc}'")
            for reg in sorted(epever.getRegisterList(fc)):
                print (f"---------- Register '{reg}'")
                p = epever.read(fc, int(hex(int(reg,16)),16))   
                await asyncio.sleep(interval.value)

async def TaskErrorTest(interval, error):
    import random
    random.seed(100)
    while True:
        error.errID(random.randint(1,7))
        error.value(error.error_interval())
        print (f"simulate error {error.errID()}")
        await asyncio.sleep(interval.value)
              
        
async def main():
    errObj = ErrorObj(idle_interval=os.getenv('HEARTBEAT_IDLE_INTERVAL'), error_interval=os.getenv('HEARTBEAT_ERROR_INTERVAL'))
    #bms_interval =  Interval(os.getenv('BMS_INTERVAL'))
    epever_interval =  Interval(os.getenv('EPEVER_INTERVAL'))
    #soyo_interval =  Interval(os.getenv('SOYO_INTERVAL'))
    hb_interval = Interval(os.getenv('HEARTBEAT_INTERVAL'))
    err_interval = Interval(30000)
    
    #bms_task = asyncio.create_task(TaskBMS(bms,bms_interval,errObj))
    epever_task = asyncio.create_task(TaskEPEVER(epever,epever_interval,errObj))
    #soyo_task_read = asyncio.create_task(TaskReadLimiter(soyo,soyo_interval,errObj))
    hb_task = asyncio.create_task(TaskHeartBeat(hb_interval,errObj))
    #err_task = asyncio.create_task(TaskErrorTest(err_interval,errObj))
    
#    await asyncio.gather(bms_task,soyo_task_read, hb_task)
    await asyncio.gather(epever_task, hb_task)


asyncio.run(main())

#    if os.getenv('BMS_DEMO'):
#        print ("\n\n-------- BYE -- END - DEMO -------- ")
#        break
