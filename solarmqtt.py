import os
import ipaddress
import wifi
import ssl
import socketpool
import adafruit_minimqtt.adafruit_minimqtt as MQTT
import time
import adafruit_logging as logging


class SolarMQTT():
    """
    Standart MQTT client to read/write data to an topic on an MQTT-Broker
    """
    def __init__(self, wifi):
        self.log = logging.getLogger('MQTT')        
        self.log.setLevel(os.getenv('MQTT_LOGLEVEL'))
        self.mqtt_topic = f"/{os.getenv('MQTT_PREFIX')}/{os.getenv('MQTT_TOPIC')}" 
        ipv4 = ipaddress.ip_address(os.getenv('MQTT_BROKER_IP'))
        self.log.info("Ping configured MQTT-Broker: %f ms" % (wifi.radio.ping(ipv4)*1000))
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
        self.log.info ("MQTT-Client initialized")
        self.log.info ("Connecting MQTT-Broker...")
        self.mqtt_client.connect()


    def connected(self, client, userdata, flags, rc):
        """ callback after successfully connectioin to broker"""
        self.log.info(f"MQTT-Broker on IP: {os.getenv('MQTT_BROKER_IP')}:{os.getenv('MQTT_PORT')} conneted to topic '{self.mqtt_topic}'")
        client.subscribe(self.mqtt_topic)

    def disconnected(self, client, userdata, rc):
        """ callback after successfully disconnection from MQTT-Broker"""
        self.log.info("Disconnected from MQTT-Broker")
        
    def subscription(self, client, topic, message):
        """ callback if message arrived from MQTT-Broker"""
        self.log.info(f"Subscription - TOPIC: ({topic})\tDATA: ({message})")
        self.log.info("New message on topic {0}: {1}".format(topic, message))
        #
        #
        # <implement your own code here>
        
    def publish(self, topic, message):
        """ send a message to MQTT-Broker"""
        self.log.info(f"Publish - TOPIC: '{topic}' ==> DATA: '{message}'")
        self.mqtt_client.publish(topic, message)

    def getSubTopic(self, subtopic):
        return f"""{self.mqtt_topic}/{subtopic}"""


class IOBrokerMQTT():
    """
    Wrapper-Class for MQTT. This class publish EPEVER specific data into an EPEVER topic/subtopic
    
    """
    def __init__(self,mqtt):
        self.mqtt = mqtt
        
    def publish(self, payload, topic_key="identifier"):
        """
        send payload to topic.
        sub-topic is used from key "identifier"

        Arguments:
        root_topic      root element in MQTT-Broker
        payload         Data to transfer
                        payload struct:
                        {'len': 2, 'info': 'Solar charger PV-voltage', 'value': 95.61, 'identifier': 'B1', 'register': '3100', 'unit': 'V', 'fcode': '04'}

        """
        rc = 1
        if payload != None:
            if len(payload) == 7:	# payload must contain 7 keys
                if 'value' in payload:
                    data = f"{payload['value']}"
                    topic_key = ('identifier' if 'identifier' not in payload else topic_key)
                    topic = self.mqtt.getSubTopic(payload[topic_key])
                    last_topic = self.mqtt.getSubTopic("_LAST_DATA_")
                    self.mqtt.publish(topic, data)
                    self.mqtt.publish(last_topic, str(payload))
                    rc = 0
                else:
                    print ("'value' key not found in payload")
            else:
                print (f"payload len({len(payload)}) to short => {payload}")
        else:
            print ("Payload is none - ignore MQTT-publish")
        # if not 0, than we have an MQTT problem
        return rc
