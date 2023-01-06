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
        log.info("Ping configured MQTT-Broker: %f ms" % (wifi.radio.ping(ipv4)*1000))
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
        print ("MQTT-Client initialized")
        print("Connecting MQTT-Broker...")
        self.mqtt_client.connect()


    def connected(self, client, userdata, flags, rc):
        """ callback after successfully connectioin to broker"""
        print(f"MQTT-Broker on IP: {os.getenv('MQTT_BROKER_IP')}:{os.getenv('MQTT_PORT')} conneted to topic '{mqtt_topic}'")
        client.subscribe(self.mqtt_topic)

    def disconnected(self, client, userdata, rc):
        """ callback after successfully disconnection from MQTT-Broker"""
        print("Disconnected from MQTT-Broker")
        
    def subscription(self, client, topic, message):
        """ callback if message arrived from MQTT-Broker"""
        print("New message on topic {0}: {1}".format(topic, message))
        
    def publish(self, topic, message):
        """ send a message to MQTT-Broker"""
        self.client.publish(topic, message)

    def getSubTopic(self, subtopic):
        return f"""{self.mqtt_topic}/{subtopic}"""


class IOBrokerMQTT(SolarMQTT):
    """
    specialized MQTT-Client to work with Solar-Data structs and send them to an MQTT-ioBroker
    """
    def __init__(self,wifi):
        super().__init__(wifi)
        
    def publish(self, topic, payload):
        """
        send payload to topic.
        
        payload struct:
        
        Topic:
        topic is the root element combinded with <register> as sub topic followed by
        """
        
        