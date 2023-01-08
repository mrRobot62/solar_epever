import adafruit_logging as logging


class MQTTHandler (Handler):
    """FMQTT for working with log to an MQTT topic
    :param str topic: Topic name to publish log data
    """

    def __init__(self, mqtt, topic: str) -> None:
        # pylint: disable=consider-using-with
        self._mqtt = mqtt
        self._topic = topic
        pass

    def close(self) -> None:
        """Closes the file"""
        pass

    def format(self, record: LogRecord) -> str:
        """Generate a string to log
        :param record: The record (message object) to be logged
        """
        return super().format(record) + "\r\n"

    def emit(self, record: LogRecord) -> None:
        """Generate the message and write it to the UART.
        :param record: The record (message object) to be logged
        """
        self.stream.write(self.format(record))