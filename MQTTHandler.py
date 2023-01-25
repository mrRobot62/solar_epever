import adafruit_logging as logging
import os


class MQTTHandler (logging.Handler):
    """FMQTT for working with log to an MQTT topic
    :param str topic: Topic name to publish log data
    """

    def __init__(self, mqtt, topic: str, subtopic : str = None) -> None:
        """ 
        MQTT Logging Handler, log data into topic/subtopic

        Args:
        mqtt        MQTT-Object 
        topic       root topic 
        subtopic    subtopic 
        """
        # pylint: disable=consider-using-with
        super().__init__()
        self._mqtt = mqtt
        self._topic = topic
        self._topic = (f"/{self._topic}/log" if subtopic is None else f"/{self._topic}/{subtopic}/log")
        print (f"MQTTHandler log into {self._topic}")

    def close(self) -> None:
        """Closes the file"""
        pass

    def format(self, record: LogRecord) -> str:
        """Generate a string to log
        :param record: The record (message object) to be logged
        """
        return super().format(record)

    def emit(self, record: LogRecord) -> None:
        """Generate the message and write it to the MQTT-TOPIC.
        :param record: The record (message object) to be logged
        """
        #print (f"MQTTHandler::emit => {record}")
        if self._mqtt is not None:
            #print (f"MQTTHandler publish {self._topic} - {self.format(record)}")
            msg = self.format(record)
            if len(msg) > 0:
                self._mqtt.publish(self._topic, msg)
            else:
                print ("##### ignore empty log entry #####")
            pass
        