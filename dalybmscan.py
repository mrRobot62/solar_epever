import os
import board
import busio
import digitalio
import time
import binascii
from struct import *

class DalyBMS():
    LOGO="""                                                
     ____   _____  __     __ __  _____  _____  _____ 
    |    \ |  _  ||  |   |  |  || __  ||     ||   __|
    |  |  ||     ||  |__ |_   _|| __ -|| | | ||__   |
    |____/ |__|__||_____|  |_|  |_____||_|_|_||_____|
                                                                                     
    """
    VERSION = os.getenv('DALYBMS_VERSION')
    _cmds = {
        #		18=Prio, 10=DataID, 01=BMSaddress, 80=HostAddress
        "10" : "181001400000000000000000",
        "90" : "189001400000000000000000",
    }
    # only for demo-mode
    _payload = {
        "90" : ["a501900800f80000753001815d"],
        "91" : ["a50191080c52050b6b0101819b"],
        "92" : ["a50192083d013d016b010181aa"],
        "93" : ["a50193080001002500009de9ed"],
        "94" : ["a501940808010000000001327e"],
        "95" : ["a5019508010b6b0c420c433289a5019508020c3c0c520c43326ca5019508030c000c480c433227"],
        "96" : ["a5019608013d000000000032b4"],
        "97" : ["a50197089000000000000000d5"],
        "98" : ["a5019808000000000000100056"]
    }

    def __init__(self, uart):
        self._uart = uart
        #self._demo_mode = (True if os.getenv("BMS_DEMO").lower() == "true" else False)
        self._demo_mode=False
        print(self.LOGO)
        print(self.VERSION)
        if self._demo_mode:
            print ("------- DEMO-MODE -------")
        self._cmditer = iter(self._cmds)
        
        pass
    
    def getCMDiterator(self):
        """ return an iterator from command list """
        return iter(self._cmds)
    
    def nextCMD(self):
        """ use internal iterator, return next command """
        return next(self._cmditer)
    
    def getRegisterCMD(self,register):
        """ return a BMS send command for a register """
        if register in self._cmds:
            return self._cmds[register]
        return None
    
    def getRegisterList(self):
        """ return a list from all BMS register """
        return self._cmds.keys()
    
    
    def crc(self, data, hasCRC=False):
        """
        Calculate check sum from data byte array and add this crc byte at the end
        Return data inkl. crc byte

        BMS CRC is sum of all bytes and than low byte

        Args:
        data	bytearry	contain data to calculate a crc sum
        hasCRC bool		default false, if True, than data contain a crc and we calculate a new crc with n-1 bytes

        Return
        data 	bytearray	including a crc sum
        None	if containCRC was set to True and data contains a crc, but calculated crc is different.

        """
        if hasCRC:
            crc1 = sum(data[:-1]) & 0xFF
            crc2 = data[-1]
            if crc1 != crc2:
                return None
        else:
            crc = sum(data) & 0xFF
            data.append(crc)

        return data

    def writeBMS(self, data):
        nbytes = self._uart.write(binascii.unhexlify(data))
        print(f"\tBytes written ({nbytes}) => {binascii.unhexlify(data)}")
        return nbytes   

    
    def readBMSRaw(self, nbytes=0,retries=3, cmd=None):
        """
        Read data from BMS in a raw format (byte array).

        Args:
        nbytes 	(int)		: default 0 = as much as possible bytes read. If set read nbytes (faster)
        cmd		(string)	: only for demo. Set self._payload key (command) (e.g. 90, 91, ...)

        Return:
        buffer				: Return byte array or None if buffer is empty
        """
        cnt = 0
        crc_ok = False
        while cnt < retries:
            buffer = bytearray()
            single = bytearray()
            if nbytes > 0:
                buffer.extend(uart.read(nbytes))
            else:
                try:
                    if self._demo_mode == False:
                        single.extend(self._uart.read())
                    else:
                        print (f"DEMO - '{self._payload[cmd]}'")
                        single.extend(binascii.unhexlify(self._payload[cmd][0]))

                except Exception as err:
                    print (f"Error occured : '{str(err)}'")
                    cnt += 1
                    continue
                #if self.crc(single,True) == False:
                #    cnt += 1
                #    print(f"({cnt}/{retries}::readBMS() - retry")
                #else:
                crc_ok = True
                buffer.extend(single)
                if crc_ok:
                    break
            pass #while


        if buffer is not None:
            print (f"\tBytes {len(buffer)} read: '{buffer}'")

            #if cmd is not None:
            #    buffer=binascii.unhexlify(self._payload[cmd][0])
        else:
            print ("\tempty buffer")
            buffer = None

        return buffer
    
    def convertData(self, data):
        """ convert raw bms data into human readable data """
        if len(data) <= 1:
            print ("no BMS data")
            return []
        l = len(data) - 3
        print (f"LEN(DATA) {len(data)}")
        pad = f">BBB{''.join(['x' for i in range(l)])}"
        #print (f"({len(data)}) Type '{type(data)}'=> '{data}'")
        cmd_block = unpack(pad, data)
        cmd = cmd_block[2]
        #print (cmd_block)
        result = []

        if cmd == 0x90:
            # BatSOC
            d_tuple = unpack(">xxxxhhhhx",data)
            unpacked = [i for i in d_tuple]
            unpacked[0] /= 10
            unpacked[1] /= 10
            unpacked[2] = unpacked[2] - 30000
            unpacked[3] /= 10
            r = {hex(cmd):unpacked}
            result.append(r)
            return result
        elif cmd == 0x91:
            # Bat Min/Max mV
            d_tuple = unpack(">xxxxhBhBxxx",data)
            unpacked = [i for i in d_tuple]
            unpacked[0] /= 1000
            unpacked[2] /= 1000
            r = {hex(cmd):unpacked}
            result.append(r)
            return result
        elif cmd == 0x92:
            # Bat Min/Max Temp
            d_tuple = unpack(">xxxxBBBBxxxxx",data)
            unpacked = [i for i in d_tuple]
            unpacked[0] = (unpacked[0] - 40 if unpacked[0] > 0.0 else 0.0)
            unpacked[2] = (unpacked[2] - 40 if unpacked[2] > 0.0 else 0.0)
            r = {hex(cmd):unpacked}
            result.append(r)
            return result

        elif cmd == 0x93:
            # Bat Charge/Discharge
            d_tuple = unpack(">xxxxBBBBlx",data)
            unpacked = [i for i in d_tuple]
            r = {hex(cmd):unpacked}
            result.append(r)
            return result

        elif cmd == 0x94:
            # Bat Status Info
            d_tuple = unpack(">xxxxBBBBBxxxx",data)
            unpacked = [i for i in d_tuple]
            r = {hex(cmd):unpacked}
            result.append(r)
            return result

        elif cmd == 0x95:
            # Bat CellVoltagea
            # split stream into frames
            s = binascii.hexlify(data).decode()
            frames = s.split('a5019508')
            for i in range(1,len(frames)):
                d_tuple = unpack(">Bhhhxx",binascii.unhexlify(frames[i]))
                unpacked = [i for i in d_tuple]
                del unpacked[0]
                r = {hex(cmd):{str(i):unpacked}}
                result.append(r)
            return result

        elif cmd == 0x96:
            # Bat Cell-Temperatures
            pass
        elif cmd == 0x97:
            # Bat Balance State
            pass
        elif cmd == 0x98:
            # Bat failure status
            d_tuple = unpack(">xxxxBBBBBBxxx",data)
            unpacked = [i for i in d_tuple]
            for i in range(6):
                unpacked[i] = bin(int(str(unpacked[i]),10))

            r = {hex(cmd):unpacked}
            result.append(r)
            return result
        else:
            # error
            return "error"
            pass    
    
    def BatterySOC(self):
        nbytes = bms.writeBMS(self.getRegisterCMD("90"))
        data = bms.readBMSRaw(cmd=register)
        result = bms.convertData(data)
        



UART1_TX = eval(f"board.{os.getenv('UART1_TX')}")
UART1_RX = eval(f"board.{os.getenv('UART1_RX')}")
uart = busio.UART(UART1_TX, UART1_RX, baudrate=os.getenv('DALYBMS_BAUD'))
bms = DalyBMS(uart)

while True:
    for register in sorted(bms.getRegisterList()):
        print (f"\n-- 0x{register} ------------------------")
        print(f"==> Send command '{bms.getRegisterCMD(register)}'")
        nbytes = bms.writeBMS(bms.getRegisterCMD(register))
        time.sleep(0.1)
#        #data = readBMSRaw(nbytes=0, cmd=cmd)
        data = bms.readBMSRaw(cmd=register)
        print(f"<== BMS data received '{binascii.hexlify(data)}'")
        #result = bms.convertData(data)
        #print(f"Data from BMS '{result}'")

        time.sleep(1)