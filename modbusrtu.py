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
import adafruit_logging as logging

class ModBusRTU():
    """
    simple ModBus RTU implementation to communicate with a ModBus slave
    
    ModBus data structure:
    <slaveid><functioncode><register><numberOfRegisters><crc>
    
    <slaveid> 			= on byte, range 0-247
    <functioncode>		= one byte
    <register>			= two bytes
    <numberOfRegisters> = two bytes
    <crc>				= two bytes
    
    <functioncodes>
    01	= Read discrete Coil 		(DO - digital output)
    02 	= Read discrete input		(DI - digital input)
    03 	= Read holding register		(AO	- analog output)
    04 	= Read input register		(AI - analog input)
    05	= Write single coil			
    15 	= Write multiple coild
    06	= Write single holding register
    16	= Write multiple holding register
    
    
    
    """
    # demo payloads from a ModBus Slave
    # all payloads asume slaveID = 01
    # structure {<func> : {<register>:<payload>}}
    demo_payloads = {
        "01" : {},    
        "02" : {},    
        "03" : {"3100":'010306AE415652434049AD'},    
        "04" : {
            "3100": '0104020A663FBA', # ~PV-VOLT ca. 26.9V (send: 01 04 31 00  00 01 3F 36)
            "3101": '0104020000B930', # ~PV-Current 0A (send: 01 04 31 01  00 01 6E F6)
            "3102": '010404000000FB84' # ~PV-Power 1W (send: 01 04 31 02  00 02 DE F7 : Note : 2 Registers are read (H & L Register 3102 & 3103)
                
        },   	 
    }
    
    def __init__(self, uart, slaveID=1, demo=False):
        self._uart = uart
        if self._uart is None:
            self.log.warning("SET DEMO-MODE due to no uart object")
            demo = True
        if slaveID < 0 or slaveID > 0xF7:	# max SlaveID = 247
            slaveID = 1
        self._sid = slaveID
        self._demo = demo					# if true, no uart activities are done, return values are simulated. Used for tests
        if self._demo:
            self.log.warning(">>>>>>>>>> DEMO-MODE <<<<<<<<<<<<")
        self._func = self._address = self._quantity = None
        self.log = logging.getLogger('MODBUS')
        self.log.setLevel(30)	# 10=Debug, 20=Info, 30=Warning, 40=Error, 50=Critical
            
            
    def getDemoPayload(self, func, register):
        payload = None
        if func in self.demo_payloads:
            addresses = self.demo_payloads[func]
            if register in addresses:
                payload = addresses[register]
        return payload
        
    def crc16(self, data, hasCRC=False, swapByte=True):
        """
        generate ModBus RTU CRC16
        
        Arguments:
        data	byte array	generate crc16 from this data
        hasCRC  bool		if true last two bytes are crc16 value, exclude this two bytes
        
        Return:
        crc		int		return a two bytes crc16 sum
        """
        crc  = 0xFFFF
        if hasCRC :
            tmpData = data[:-4]	# remove last two bytes
        else:
            tmpData = data
        nbytes = len(tmpData)/2
        for p in range(nbytes):
            #print (f"({p}) Byte ({binascii.unhexlify(tmpData)[p]})")
            crc ^= binascii.unhexlify(tmpData)[p]	# XOR byte into least sig byte of crc
            for i in range (8):						# loop over each bit
                if ((crc & 0x0001) != 0):			# if the lsb is set
                    crc >>= 1						# shift right and XOR 0xA001 (polynominal 0xA001 CRC)
                    crc ^= 0xA001					# 
                else:								# else LsB is not set
                    crc >>= 1						# just shift ro right
        # Note, this number has low and high bytes swapped, so use it accordingly (or swap bytes)
        if swapByte:
            msb = crc >> 8
            lsb = crc & 0xFF
            #print (f"MSB ({hex(msb).upper()}) LSB ({hex(lsb)})")
            crc = lsb << 8 | msb
        return crc
    
    def decode(self, data, func=None, fmt=">BBhhH"):
        """
        decode data due to unpacking formating string
        
        Arguments:
        data		bytearray	data to decode
        func		string		"01","02",... if set, than try to decode data for this function
        fmt			string		unpacking formatting string. See: https://docs.micropython.org/en/latest/library/struct.html?highlight=unpack
        """
        d_tuple = unpack(fmt,binascii.unhexlify(data))
        unpacked = [hex(i) for i in d_tuple]
        data = {}
        
        func = ("UNKNOWN" if func is None else func)    
        data = {func:unpacked}
        return data
        
        
    def receive(self, returnByteArray=False):
        """
        read bytes from ModBus slave and return raw list
        
        """
        buffer = []
        try:
            if self._demo == False:
                buffer.extend(self._uart.read())
            else:
                buffer = bytearray(self.getDemoPayload(self._func, self._address))
        except:
            buffer = []
        #print (f"BUFFER: {buffer}")
        buffer = (''.join(f'{i:02x}' for i in buffer) if returnByteArray else buffer)
        self.log.debug(f"{type(buffer)} -> {buffer}")
        #print (f"{type(buffer)} -> {buffer}")            
        return buffer    
    
    def send(self, func, register, quantity=1, swapBytes=True):
        """
        generate a ModBus RTU byte array
        
        Arguments:
        func		string	01-06,15,16
                            01 = Read Coils
                            02 = Read discrete inputs
                            03 = Read Holding Register
                            04 = Read input Register
                            05 = Write single coil
                            15 = Write multiple coil
                            06 = Write single holding register
                            16 = Write multiple holding register
        register 	int		hex register to read/write e.g. 0x3100, 0x2501, ...
        quantity	byte	hex number of registers to read (default 1) (max 0xFF)
        """
        if quantity > 0xFF:
            quantity = 0xFF
        # write sequences are different
        if func == "05":
            p = f""
        elif func == "06":
            p = f""
        elif func == "15":
            p = f""
        elif func == "16":
            p = f""
        else:
            # all other function codes use the same structure
            p = f"{self._sid:02d}{func}{register:04x}{quantity:04x}"
        self._func = func
        self._address = f"{register:04x}"
        self._quantity = f"{quantity:04x}"

        data = bytearray(p)
        crc = self.crc16(data, hasCRC=False, swapByte=True)
        self.log.debug(f"CRC: {hex(crc)}")
        data.extend(f"{(crc >> 8):02x}")		# add MSB
        data.extend(f"{(crc & 0xFF):02x}")		# add LSB
        self.log.debug(str(data))
        
        try:
            if self._demo == False:
                nbytes = self._uart.write(binascii.unhexlify(data))
            else:
                self.log.warning(f"DEMO_MODE_WRITE {str(data)}")
                nbytes = int(len(data)/2)
        except:
            return 0
        return nbytes, data
