# EPEVER solar charger - ModBus via RP2040 CircuitPython
Written with CircuitPython for a Raspberry RP2040 PICO W board. The software run asynchron an read all configured registers out from the EPEVER device.
Via MQTT data can be send to a MQTT-Broker (in my case ioBroker with installed MQTT extension)

## History
|Version|Date|Info|
|---|---|---|
|0.1.0|2023-01-05|initial version working with EPEVER XTRA 4415n|
||||

# Quick Overview
The software is devided into several parts and classes

* **SolarPICO:** Main modul. From here all other parts are called
* **ModBusRTU:** Base class for ModBus devices
* **EPEPVER:** Define all function codes and register for reading, decoding and converting data
* **SolarMQTT:** Simple class to send data to a MQTT-Broker
* **settings.toml** Configuration file
* **folder lib** includes all necessary adafruit libraries

# Dependencies
* You need a [PICO with WLAN](https://www.raspberrypi.com/documentation/microcontrollers/raspberry-pi-pico.html#raspberry-pi-pico-w-and-pico-wh)
* [CircuitPython 8.0.x](https://circuitpython.org/board/raspberry_pi_pico/) installed on your RP204 device. Software was not tested with 7.3.x
* Connection cable to your EPEVER device. Use an standard RJ45 Ethernet cable and cut on plug to connecto the RS485 adapter
* Adapter to convert RS485 to UART => [Amazon-Link](https://www.amazon.de/DollaTek-RS485-Adapter-Serieller-Converter/dp/B07DJ4TGY3/ref=sr_1_10?__mk_de_DE=ÅMÅŽÕÑ&crid=161SDT8U5CSX3&keywords=RS485+adapter&qid=1672887030&sprefix=rs485+adapter%2Caps%2C93&sr=8-10)

<img src="img/RS485_UART.png" width="200">

* Install [Thonny-IDE](https://thonny.org) for easy working with your [PICO](https://www.raspberrypi.com/documentation/microcontrollers/raspberry-pi-pico.html). Follow installation instructions

# Installation
* install CircuitPython on your device. Please follow instruction form [CircuitPython.org](https://docs.circuitpython.org/en/latest/README.html#get-circuitpython).
* Test your RP2040. Is it connected to your computer? Can you access to the device with your file explorer?
* download this github repo to your local computer into a folder
* copy all content from this folder onto your [PICO](https://www.raspberrypi.com/documentation/microcontrollers/raspberry-pi-pico.html)
# Configuration
Open in Thonny the file `settings.toml`

## WLAN
Configure your SSID and password for access to your WLAN. If configured, please restart your PICO and check if this device can be pinged

```
################################################
# WiFI-Configuration
#
################################################
CIRCUITPY_WIFI_SSID="<ssid>"
CIRCUITPY_WIFI_PASSWORD="<password>"
```
## General settings
Normaly you should nothing change in this section
```
################################################
# GENERAL
################################################
# 10=Debug, 20=Info, 30=Warning, 40=Error, 50=Critical
UART0_TX = "GP0"
UART0_RX = "GP1"
UART1_TX = "GP4"
UART1_RX = "GP5"
```
## EPEVER
* `EPEVER_UART`. Please configure 0 (UART0) or 1 (UART1)
* `EPEVER_LOGLEVEL` explicit EPEVER logging level.
* `EPEVER_INTERVAL` how often should the registered read (in milliseconds). Avoid to fast reading (< 500)

```
################################################
# EPEVER
################################################
EPEVER_DEMO="True"
EPEVER_INTERVAL = 5000
EPEVER_VERSION = "V 0.1.0"
EPEVER_UART=1
# 10=Debug, 20=Info, 30=Warning, 40=Error, 50=Critical
EPEVER_LOGLEVEL=20
```

## MQTT

* `MQTT_BROKER_IP` : insert the IP-Adress from your MQTT-Broker
* `MQTT_PORT` : default port is 1883
* `MQTT_PREFIX` : root folder in the topic payload. 
* `MQTT_TOPIC` : topic name (e.g. DeviceName)
* `MQTT_USER` : MQTT-User
* `MQTT_PW` : MQTT-Users password
* `MQTT_LOGLEVEL` : explicit MQTT Logging level

``` 
################################################
# MQTT-Configuration
################################################
MQTT_BROKER_IP="<mqtt-broker ip address>"
MQTT_PORT=1883
MQTT_PREFIX="RP2040_SOLAR"
MQTT_TOPIC="EPEVER"
MQTT_USER="<user>"
MQTT_PW="<password>"
# 10=Debug, 20=Info, 30=Warning, 40=Error, 50=Critical
MQTT_LOGLEVEL=20

``` 

## HeardBeat
This section is used to indicates, that the system is running or if an error occured wit a blinking led

* `HEARTBEAT_INTERVAL` how often a heart beat signal should raised (default 5000ms)
* `HEARTBEAT_IDLE_INTERVAL` used as blinking frequence (do not change)
* `HEARTBEAT_ERROR_INTERVAL` if an error occured, this this the blinking frequence (default 500ms, 2x sec)
* `HEARTBEAT_IDLE` if no error occured, PICO blinks 1x per `HEARTBEAT_IDLE_INTERVAL`
* `HEARTBEAT_ERROR_MODBUS` blinks 3x times if something goes wrong with your modbus device
* `HEARTBEAT_ERROR_MQTT` blinks 6x if something goes wrong with MQTT
* `HEARTBEAT_ERROR_WLAN` blinks 5x if something goes wrong with your WLAN connection


``` 
################################################
# HEART-BEAT
################################################
HEARTBEAT_INTERVAL = 5000
HEARTBEAT_IDLE_INTERVAL = 150
HEARTBEAT_ERROR_INTERVAL = 500
HEARTBEAT_IDLE = 1
HEARTBEAT_ERROR_BMS = 2
HEARTBEAT_ERROR_MODBUS = 3
HEARTBEAT_ERROR_INVERTER = 4
HEARTBEAT_ERROR_WLAN = 5
HEARTBEAT_ERROR_MQTT = 6
``` 
# SolarPICO.py
Central script to call periodically the EPEPER device and send the result via MQTT to your Broker
## Class Interval
Only used for storing an interval value for running tasks

## Class ErrObj
Only used to store an error code. This code indicates the error with a blinking led on your PICO 

# Class EPEVER

# Class ModBusRTU

# Class SolarMQTT

