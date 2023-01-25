"""
License: see license_gpl-3.0.txt
"""
import board
import os
import busio
import digitalio
import time
import binascii
from struct import *
from modbusrtu import ModBusRTU
import adafruit_logging as logging
import json
import rtc
import adafruit_ntp

class EPEVER(ModBusRTU):
    LOGO="""
 _____  _____  _____  _____  _____  _____ 
|   __||  _  ||   __||  |  ||   __|| __  |
|   __||   __||   __||  |  ||   __||    -|
|_____||__|   |_____| \___/ |_____||__|__|                                                                                                                               
    """
    VERSION = os.getenv('EPEVER_VERSION')
    
    # {<functioncode> : {<register> : {<type>, <unit>, <scale>, <format>}}
    fCode = {
        # Read Holding Register (0x03) and Write Multiple Holding Register (0x10)
        # Setting Parameter (Read and Write)
        "03": {
            "9000": {"identifier": "BATTERY_TYPE_9000", "unit":"type", "convert":"dec", "scale":1, "quantity":1, "fmt":'>BBBHxx',"demo":'0103020000b844', "info":""},
            "9001": {"identifier": "BATTERY_CAPACITY_9001", "unit":"'Ah", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx',"demo":'0103020069786a', "info":""},
            "9002": {"identifier": "TEMPERATUR_COEF_9002", "unit":"mV", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx',"demo":'0103020000b844', "info":""},
            "9013": {"identifier": "RealTimeClock", "unit":"Date", "convert":"time", "scale":1, "quantity":3, "fmt":'>xxxBBBBBBxx',"demo":'3001121317', "info":"Read internal RealTimeClock"},

        },
        # Read Input Register(0x04)
        "04" : {
            # Rated datum (read-only)
            "3000": {"identifier": "PV_RATED_VOLT_3000", "unit":"V", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx',"demo":'0104023a98aa3a', "info":"PV array rated voltage"}, # 
            "3001": {"identifier": "PV_RATED_CURRENT_3001", "unit":"A", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx',"demo":'0104020fa0bcb8', "info":"PV array rated current"}, # 
            "3002": {"identifier": "PV_RATED_POWER_3002", "unit":"W", "convert":"dec", "scale":100, "quantity":2, "fmt":'>BBBHHxx',"demo":'0104042c800003b2fd', "info":"PV array rated power (L=16bit, H=16Bit at 0x3003)"}, # 
            "3004": {"identifier": "BAT_RATED_VOLT_3004", "unit":"V", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx',"demo":'01040212c0b5c0', "info":"Rated voltage to bat"}, # 
            "3005": {"identifier": "BAT_RATED_CURRENT_3005", "unit":"A", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx',"demo":'0104020fa0bcb8', "info":"Rated current to bat"}, # 
            "3006": {"identifier": "BAT_RATED_POWER_3006", "unit":"W", "convert":"dec", "scale":100, "quantity":2, "fmt":'>BBBHHxx',"demo":'0104042c800003b2fd', "info":"Rated power to bat (L & H (0x3007)"}, # 
            "3008": {"identifier": "CONNECTED_3008", "unit":"-", "convert":"bin", "scale":100, "quantity":1, "fmt":'>BBBHxx',"demo":'010402000238f1', "info":"Connect/disconnect"}, # 
            "300E": {"identifier": "LOAD_RATED_CURRENT_300E", "unit":"W", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx',"demo":'0104020fa0bcb8', "info":"rated current of load"}, #
            # real-time datum (read-only)
            "3100": {"identifier": "PV_ARRAY_INPUT_VOLT_3100", "unit":"V", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx',"demo":'0104022559639a', "info":"Solar charger PV-voltage"}, # 
            "3101": {"identifier": "PV_ARRAY_INPUT_CURRENT_3101", "unit":"A", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx',"demo":'01040200e3f8b9', "info":"Solar charger PV-current"}, # 
            "3102": {"identifier": "PV_ARRAY_INPUT_3102", "unit":"W", "convert":"dec", "scale":100, "quantity":2, "fmt":'>BBBHHxx',"demo":'010404593b000098d5', "info":"Solar PV-Power L (0x3103 PV-Power H)"},	# 
            "3106": {"identifier": "BATTERY_POWER_3106", "unit":"W", "convert":"dec", "scale":100, "quantity":2, "fmt":'>BBBHHxx',"demo":'010404708c000020af', "info":"Solar Bat-Power L (0x3107 Bat-Power H)"},	# 
            "310C": {"identifier": "LOAD_VOLTAGE_310C", "unit":"V", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx',"demo":'0104020000b930', "info":"Load voltage"}, # 
            "310D": {"identifier": "LOAD_CURRENT_310D", "unit":"A", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx',"demo":'0104020000b930', "info":"Load current"}, # 
            "310E": {"identifier": "LOAD_POWER_310E", "unit":"W", "convert":"dec", "scale":100, "quantity":2, "fmt":'>BBBHHxx',"demo":'01040400000000fb84', "info":"Load Power L (0x310F H)"}, # 
            "3110": {"identifier": "TEMP_BATTERY_3110", "unit":"°C", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx',"demo":'0104020bbd7e71', "info":"Bat Temp"}, # 
            "3111": {"identifier": "TEMP_INSIDE_3111", "unit":"°C", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx',"demo":'0104020ffbfd43', "info":"Temp inside charger"}, # 
            "311A": {"identifier": "BATTERY_SOC_311A", "unit":"%%", "convert":"dec", "scale":1, "quantity":1, "fmt":'>BBBHxx',"demo":'0104020027f92a', "info":"Bat SOC"}, # 
            "311B": {"identifier": "BATTERY_REMOTE_TEMP_311B", "unit":"°C", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx',"demo":'0104020000b930', "info":"Bat Temp remote sensor"}, # 
            "311D": {"identifier": "BATTERY_REAL_RATED_POWER_311D", "unit":"V", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx',"demo":'0104020960bf48', "info":"current system rated voltage"}, # 

            # Real-time status (read only)
            "3200": {"identifier": "BATTERY_STATUS_BIT_3200", "unit":"-", "convert":"bin", "scale":1, "quantity":1, "fmt":'>BBBHxx',"demo":'0104020000b930', "info":"Bat Status 16Bit-Field"}, # 
            "3201": {"identifier": "CHARGING_STATUS_BIT_3201", "unit":"-", "convert":"bin", "scale":1, "quantity":1, "fmt":'>BBBHxx',"demo":'010402000bf8f7', "info":"Charging status 16Bit-Field"}, # 
            "3202": {"identifier": "DISCHARGE_STATUS_BIT_3202", "unit":"-", "convert":"bin", "scale":1, "quantity":1, "fmt":'>BBBHxx',"demo":'0104020000b930', "info":"Discharging status 16Bit-Field"}, # 

            # Statistical prameters (read only)
            "3300": {"identifier": "STAT_PV_MAX_TODAY_3300", "unit":"V", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx',"demo":'0104022fbca4b1', "info":"Max PV volt today"}, 	# 
            "3301": {"identifier": "STAT_PV_MIN_TODAY_3301", "unit":"V", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx',"demo":'010402004cb8c5', "info":"Min PV vol todday"}, 	# 
            "3302": {"identifier": "STAT_BAT_MAX_TODAY_3302", "unit":"V", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx',"demo":'0104020a123f9d', "info":"Max bat volt today"}, 	# 
            "3303": {"identifier": "STAT_BAT_MIN_TODAY_3303", "unit":"V", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx',"demo":'0104020937feb6', "info":"Min bat volt today"}, 	# 
            "3304": {"identifier": "STAT_CONS_ENERGY_TODAY_3304", "unit":"kWh", "convert":"dec", "scale":100, "quantity":2, "fmt":'>BBBHHxx',"demo":'01040400000000fb84', "info":"consumed energy today L(D4) & H (D5)"}, 	# 
            "3306": {"identifier": "STAT_CONS_ENERGY_MONTH_3306", "unit":"kWh", "convert":"dec", "scale":100, "quantity":2, "fmt":'>BBBHHxx',"demo":'01040400000000fb84', "info":"consumed energy month L(D8) H(D9)"},	# 
            "3308": {"identifier": "STAT_CONS_ENERGY_YEAR_3308", "unit":"kWh", "convert":"dec", "scale":100, "quantity":2, "fmt":'>BBBHHxx',"demo":'01040400000000fb84', "info":"consumed energy year L(D8) H(D9)"},	# 
            "330A": {"identifier": "STAT_CONS_ENERGY_TOTAL_330A", "unit":"kWh", "convert":"dec", "scale":100, "quantity":2, "fmt":'>BBBHHxx',"demo":'010404000600001b85', "info":"consumed energy total L(D10) H(D11)"},	# 
            "330C": {"identifier": "STAT_GEN_ENERGY_TODAY_330C", "unit":"kWh", "convert":"dec", "scale":100, "quantity":2, "fmt":'>BBBHHxx',"demo":'010404004a0000da52', "info":"generated energy today L(D12) H(D13)"},	# 
            "330E": {"identifier": "STAT_GEN_ENERGY_MONTH_330E", "unit":"kWh", "convert":"dec", "scale":100, "quantity":2, "fmt":'>BBBHHxx',"demo":'01040400e300000a72', "info":"generated energy month L(D14) H(D15)"},	# 
            "3310": {"identifier": "STAT_GEN_ENERGY_YEAR_3310", "unit":"kWh", "convert":"dec", "scale":100, "quantity":2, "fmt":'>BBBHHxx',"demo":'01040400e300000a72', "info":"generated energy year L(D16) H(D17)"},	# 
            "3312": {"identifier": "STAT_GEN_ENERGY_TOTAL_3312", "unit":"kWh", "convert":"dec", "scale":100, "quantity":2, "fmt":'>BBBHHxx',"demo":'01040404e600001b43', "info":"generated energy total L(D18) H(D19)"},	# 
            "331A": {"identifier": "STAT_BAT_REMAIN_CAPA_331A", "unit":"V", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx',"demo":'01040209bcbed1', "info":"percentage of battery's remaining capacity"},
            "331B": {"identifier": "STAT_BAT_REMOTE_TEMP_331B", "unit":"A", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx',"demo":'010402078d7b65', "info":"Battery temperature measured by remote temperature sensor"},
            "331C": {"identifier": "STAT_SYS_RATED_VOLT_331C", "unit":"V", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx',"demo":'0104020000b930', "info":"Current system rated voltage."},
            }
        }
        
    def __init__(self,uart, logger=None, handler=None, slaveID=1, pool=None, name=None, demo=False):
        super().__init__(uart,slaveID)
        self._demo = demo
        self._pool = pool
        self._useRTCSync = (False if pool is None else True)
        
        name = (type(self).__name__ if name is None else name)
        self.name = f"{name}"
        if logger is None:
            self.log = logging.getLogger('EPEVER')
            self.log.setLevel(os.getenv('EPEVER_LOGLEVEL'))
            if handler is not None:
                self.log.info(f"Add new log handler '{handler}'")
                self.log.addHandler(handler)
        else:
            self.log = logger
        self.log.info(self.LOGO)
        self.log.info(self.VERSION)
        self.log.info(f"EPVER connected via UART={uart}")
        self.log.info(f"EPVER SlaveID={slaveID}")
        self.log.info(f"EPVER Name={name}")
        self.log.info(f"{self.name} initalized. Mode: {('>>> DEMO-MODE <<<' if self._demo else '>>> REALTIME <<<' )}")
        if self._demo:
            print("--------- EPEVER - DEMO-MODE -------------")
        else:
            print("--------- EPEVER - REAL-TIME MODE -------------")

        
    def getName(self):
        return self.name

    def getFunctionCodeList(self):
        """ return a key list from all function codes """
        return self.fCode.keys()
    
    def getRegisterList(self, fcode):
        """ return key list from all register for this fcode """
        if fcode in self.fCode:
            return self.fCode[fcode]
        
    def _registerAvailable(self, fcode, register):
        """ check if fcode and register are configured. If not return None """
        if fcode in self.fCode:
            address = str(hex(register)[2:]).upper()
            self.log.debug(f"_registerAvailable: fcode {fcode} found, {address}")
            if address in self.fCode[fcode]:
                return self.fCode[fcode][address]
            else:
                self.log.error(f"Register '{address}' not configured - ignore")
        return None
    
    def _convert2Bin(self,value):
        """ convert a value into its binary representation """
        convert = f"{bin(int(value))[2:]:0>16}" # remove 0b, create a 16bit string value
        return convert
    
    def _convertRTC(self, data):
        """
        data is the response array of 6 bytes. EPVER send in a form like this [m,s,h,D,Y,M]
        This data is converted into "YYYY-MM-DD HH:MM:SS"
        """
        YYYY = MM = DD = HH = MIN = SEC = 0
        YYYY = int(data[4])+2000
        MM = int(data[5])
        DD = int(data[3])
        HH = int(data[2])
        MIN = int(data[0])
        SEC = int(data[1])
        fmt = f"{YYYY:04d}-{MM:02d}-{DD:02d} {HH:02d}:{MIN:02d}:{SEC:02d}"
        self.log.info(fmt)
        return fmt 
        
        
    def _convertData(self, fcode, register, rcfg, data):
        """
        convert data into a human readable dict
        
        Arguments:
        fcode		current used function code
        register	current used register
        rcfg		configuration data for used register
        data		data list to convert
        
        Return
        converted 	dictionary {"fcode":<fcode>, "register": <register>, "len":<len>, "value":<value>, "unit":<unit>,"demo":'', "info":<info>}}
        """
        converted = {'fcode':'', "register":"", "len":0, "identifier":"", "unit":"","demo":'', "info":"", "value":0}
        try:
            data = data[fcode]
            converted["fcode" ]		= fcode
            converted["register"] 	= f"{register:04x}"
            converted["len"]		= int(data[2])
            converted["identifier"] = rcfg["identifier"]
            converted["unit"] 		= rcfg["unit"]
            converted["info"] 		= rcfg["info"]
            if rcfg["convert"] == "bin":
                binary = self._convert2Bin(data[3])
                converted["value"] = binary
            elif rcfg['convert'] == "dec":
                value = float(int(data[3]) / rcfg["scale"])
                converted["value"] = value
            elif rcfg['convert'] == "time":
                date = self._convertRTC(data)
                converted["value"] = date
            else:
                converted["value"] = "unknown"

        except Exception as err:
            msg = f"error in epever.py {str(err)}"
            converted["info"] = msg 
            self.log.critical(msg)
            
        self.log.info(f"EPEVER data converted: '{str(converted)}'")
        
        return converted	
        
    def read(self, fcode, register):
        """
        Read a register from EPEVER
        
        Arguments:
        fcode		string 		"01", "02", "03", "04"
        register	hexword		register address as hex value (e.g. 0x3100)
        
        Return:
        raw,converted		tuple	(raw list, converted-dict)
                            converted-dict => {"register":"<type>":"<value", "unit":<unit>}
        
        """


        regcfg = self._registerAvailable(fcode, register)
        if regcfg != None:
            converted = {}
            regKey = f"{register:04x}".upper()
            msg = f"""
---------------------------------------------------------
{self.getName()} - FCode '{fcode}'	- Register '{regKey}'
---------------------------------------------------------
"""
            self.log.info(msg)
            demoData = (self.fCode[fcode][regKey]['demo'] if self._demo else None)
            print(f"DEMO_DEMO '{demoData}'")
            nbytes, data = self.send(func=fcode,
                                     register=register,
                                     quantity=regcfg['quantity'],
                                     swapBytes=True,
                                     demo = self._demo
                                      )
            self.log.info(f"SEND:\t\t{data}\t({nbytes}) DemoData: {demoData}")
            raw = self.receive(returnByteArray=True, demoData=demoData)
            print (f"DEMO_DEMO: RAW '{raw}'")
            self.log.info(f"raw bytearray {raw} ({len(raw)}); convert with fmt='{regcfg['fmt']}'")
            if len(raw) >= 7:

                decoded = self.decode(raw,fcode, fmt=regcfg['fmt'])
                self.log.debug (f"RECEIVE:\n{raw} | {decoded}")
                converted = self._convertData(fcode, register, regcfg, decoded)
                self.log.info (f"RECEIVE:\nraw:\t\t{raw}\ndecoded:\t{decoded}\nconverted:\t{str(converted)}")
                return raw, converted
        return None, None
    # TX  01 04 31 00 00 01 3F 36 	(RTU-Software)
    #     01 04 31 00 00 01 3f 36 	(Pico)
    # RX  01 04 02 0a 81 7f f0 		(0x0A81 = 26.89V)
    
    def write (self, fcode, register, data):
        self.log.warning ("not implemented yet")
        return None
    
    def setRTC(self, pool, data):
        """
        """
        if self._useRTCSync:
            ntp = adafruit_ntp.NTP(self._pool, tz_offset=0)
            
        pass
    
# for Test purposes please remove comment char

#EPEVER_TX = eval(f"board.{os.getenv('UART1_TX')}")
#EPEVER_RX = eval(f"board.{os.getenv('UART1_RX')}")
#uart1 = busio.UART(EPEVER_TX, EPEVER_RX, baudrate=115200)

#epever = EPEVER(uart=uart1, slaveID=1)

#msg = """\n
#**********************************************************
#EPEVER ModBus - READ InputRegister (0x04) - TEST
#**********************************************************\n
#"""
#print (msg)

#while True:
#    p = epever.read("03", 0x9013)
#    time.sleep(1)



#time.sleep(2)
    
#while True:
#    print ("******************************************************")
#    for fc in sorted(epever.getFunctionCodeList()):
#        print (f">>>>>>>>> FCode '{fc}'")
#        for reg in sorted(epever.getRegisterList(fc)):
#            print (f"---------- Register '{reg}'")
#            p = epever.read(fc, int(hex(int(reg,16)),16))   
#            time.sleep(2)
#    


#----------------------------------
# below only special test scenarios
#----------------------------------

# modbus = ModBusRTU(None,1)
# 
# d0 = bytearray("0103310000018AF6")
# d1 = bytearray("010100010001AC0A")
# d2 = bytearray("0104310000013F36")
# d3 = bytearray("0103311D00011AF0")
# 
# p, data = modbus.send("03",0x3100, 0x1)
# print (f"Bytes written: {p}")
# p, data  = modbus.send("03",0x311D, 0x1)
# print (f"Bytes written: {p}")
# p, data  = modbus.send("04",0x3100, 0x1)
# print (f"Bytes written: {p}")
# p, data  = modbus.send("04",0x0031, 0x1)
# print (f"Bytes written: {p}")
# 
# p, data  = modbus.send("03",0x3100, 0x1)
# r = modbus.receive()
# print (f"Send: {p} / {data} -> Receive: {r}")
# decoded = modbus.decode(data)
# print (f"Decoded data {decoded}")
# decoded = modbus.decode(r, fmt=">BBBBHHxx")
# print (f"Decoded data {decoded}")
# #crc = epever.crc16(d1,True)
# #print (f"CRC: {crc:0}")
# 
# #crc = epever.crc16(d2,True)
# #print (f"CRC: {hex(crc).upper()}")
# 
# #crc = epever.crc16(d3,True)
# #print (f"CRC: {hex(crc).upper()}")
# 



