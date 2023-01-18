import os
import ipaddress
import wifi
import ssl
import socketpool
import adafruit_minimqtt.adafruit_minimqtt as MQTT
import time
import adafruit_logging as logging
import json

class SolarMQTT():
    """
    Standart MQTT client to read/write data to an topic on an MQTT-Broker
    """
    def __init__(self, wifi, deviceID=None):
        deviceID = ("1" if deviceID is None else str(deviceID))
        self.log = logging.getLogger(f"MQTT{deviceID}")
        #print (os.getenv('MQTT_LOGLEVEL'))
        self.log.setLevel(os.getenv('MQTT_LOGLEVEL'))

        self.mqtt_topic = f"/{os.getenv('MQTT_PREFIX')}/{os.getenv('MQTT_TOPIC')}/" 
        #self.mqtt_topic = self.pathJoin(endSlash=True, os.getenv('MQTT_PREFIX'), os.getenv('MQTT_TOPIC'))
        self.log.info(f"{SolarMQTT.__name__} Topic: {self.mqtt_topic}")
        ipv4 = ipaddress.ip_address(os.getenv('MQTT_BROKER_IP'))
        self.log.info(f"{SolarMQTT.__name__} Ping configured MQTT-Broker: {(wifi.radio.ping(ipv4)*1000)}ms")
        self.pool = socketpool.SocketPool(wifi.radio)
        self.mqtt_client = MQTT.MQTT(
            broker=os.getenv('MQTT_BROKER_IP'),
            port=os.getenv('MQTT_PORT'),
            username=os.getenv('MQTT_USER'),
            password=os.getenv('MQTT_PW'),
            socket_pool=self.pool,
            #ssl_context=ssl.create_default_context(),
        )

        self.mqtt_client.on_connect = self.connected
        self.mqtt_client.on_disconnect = self.disconnected
        self.mqtt_client.on_message = self.subscription
        self.log.info (f"{type(self).__name__} MQTT-Client initialized")
        self.log.info (f"{type(self).__name__} Connecting MQTT-Broker...")
        self.mqtt_client.connect()
        self.log.info(f"{type(self).__name__} initalized")

    def connected(self, client, userdata, flags, rc):
        """ callback after successfully connectioin to broker"""
        self.log.info(f"{type(self).__name__} MQTT-Broker on IP: {os.getenv('MQTT_BROKER_IP')}:{os.getenv('MQTT_PORT')} conneted to topic '{self.mqtt_topic}'")
        client.subscribe(self.mqtt_topic)

    def disconnected(self, client, userdata, rc):
        """ callback after successfully disconnection from MQTT-Broker"""
        self.log.info("Disconnected from MQTT-Broker")
        
    def subscription(self, client, topic, message):
        """ callback if message arrived from MQTT-Broker"""
        self.log.info(f"{type(self).__name__} Subscription - TOPIC: ({topic})\tDATA: ({message})")
        self.log.info(f"{type(self).__name__} New message on '{topic}' => {message}")
        #
        #
        # <implement your own code here>
    def pathJoin(self, endSlash=True, *args):
        path = ""
        for p in args:
            path += p
        
        if endSlash:
            path += "/"
        return path
    
    def publish(self, topic, message):
        """ send a message to MQTT-Broker"""
        self.log.info(f"{type(self).__name__} Publish - TOPIC: '{topic}' ==> DATA: '{message}'")
        self.mqtt_client.publish(topic, message)

    def getSubTopic(self, subtopic, datapoint=None, endSlash=True):
        """ genereate a topic path from main topic/subtopic/datapoint
        if datapoint is not set return only topic/subtopic
        """
        path = (self.pathJoin(endSlash,self.mqtt_topic,subtopic) if datapoint is None else self.pathJoin(endSlash,self.mqtt_topic,subtopic, datapoint))
        print(path)
        return path


class IOBrokerMQTT():
    """
    Wrapper-Class for MQTT. This class publish EPEVER specific data into an EPEVER topic/subtopic
    
    """
    def __init__(self,mqtt):
        self.mqtt = mqtt
        
        # below code send statistical informatio to your MQTT-Broker
        t1 = self.mqtt.getSubTopic(subtopic="PICO_WIFI_SSID", endSlash=True)
        t2 = self.mqtt.getSubTopic(subtopic="PICO_IP_ADDRESS", endSlash=True)
        t3 = self.mqtt.getSubTopic(subtopic="PICO_MAC", endSlash=True)
        t4 = self.mqtt.getSubTopic(subtopic="PICO_WIFI_HOSTNAME", endSlash=True)
        
        self.mqtt.publish(t1, f"{os.getenv('PICO_WIFI_SSID')}")
        self.mqtt.publish(t2, f"{wifi.radio.ipv4_address}")
        self.mqtt.publish(t3, ":".join([ f"{i:02x}" for i in wifi.radio.mac_address]).upper())
        self.mqtt.publish(t4, f"{os.getenv('PICO_WIFI_HOSTNAME')}")
        self.mqtt.log.info(f"{IOBrokerMQTT.__name__} initalized")

    def generateStatistic(self, subtopic, payload):
        """ create some statistical topics 

        Statistical attributes
        "ZZ_DATA" : json struct from payload
        "ZZ_TIME" : PICOS time.time() in milliseconds since 1970-01-01

        Arguments:
        subtopic    add this folder to root-topic
        payload     thats the current payload, this data is send as json-struct
        """    

        _data = payload
        _time = time.time()
        payload = {"identifier" : 'ZZ_DATA', "value" : json.dumps(payload)}
        print(payload)
        self.publish(subtopic, payload)
        
        payload = {"identifier" : 'ZZ_TIME', "value" : f"{time.time()}"}
        print(payload)
        self.publish(subtopic, payload)
        return 0

    def publish(self, subtopic, payload):
        """
        send payload to topic.
        sub-topic is used from key "identifier"

        Arguments:
        root_topic      root element in MQTT-Broker
        payload         Data to transfer
                        payload struct:
                        {'len': 2, 'info': 'Solar charger PV-voltage', 'value': 95.61, 'identifier': '31xx_PV_ARRAY_INPUT_VOLT_3100', 'register': '3100', 'unit': 'V', 'fcode': '04'}

        """
        rc = 1
        if payload != None:
            if 'value' in payload:
                self.mqtt.log.debug(f"{type(self).__name__}: subtopic: '{subtopic}'; payload: {payload}")
                data = f"{payload['value']}"
                datapoint = (None if 'identifier' not in payload else payload['identifier'])
                topic = self.mqtt.getSubTopic(endSlash=True, subtopic=subtopic, datapoint=datapoint)
                self.mqtt.publish(topic, data)                
                rc = 0
            else:
                self.mqtt.log.warning (f"'value' key not found in payload '{payload}'")
        else:
            self.mqtt.log.warning ("Payload is none - ignore MQTT-publish")
        # if not 0, than we have an MQTT problem
        return rc
