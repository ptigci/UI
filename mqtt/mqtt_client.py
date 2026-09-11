"""Thin wrapper around paho-mqtt for JSON publish/subscribe."""

import json
import logging

import paho.mqtt.client as mqtt

from config import MQTT_BROKER_ADDRESS, MQTT_KEEPALIVE_SECONDS, MQTT_PORT

logger = logging.getLogger(__name__)


class MqttClient:
    """Manages one broker connection. Incoming JSON messages are decoded and
    forwarded to on_message_callback on the paho network thread."""

    def __init__(self) -> None:
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message

        self.on_message_callback = None
        self.subscribed_topics: list[str] = []
        self.is_connected = False

        # connect_async + loop_start makes paho retry in the background,
        # so the UI still opens when the broker is down.
        self.client.connect_async(MQTT_BROKER_ADDRESS, MQTT_PORT, MQTT_KEEPALIVE_SECONDS)
        self.client.loop_start()

    def subscribe(self, topic: str) -> None:
        self.subscribed_topics.append(topic)
        self.client.subscribe(topic)
        logger.info(f"Subscribed to topic: {topic}")

    def publish_json(self, topic: str, payload: dict) -> None:
        serialized_payload = json.dumps(payload)
        self.client.publish(topic, serialized_payload)
        logger.info(f"Published to '{topic}': {serialized_payload}")

    def on_connect(self, client, userdata, connect_flags, reason_code, properties) -> None:
        if reason_code.is_failure:
            logger.error(f"MQTT connection failed: {reason_code}")
            return
        self.is_connected = True
        logger.info(f"Connected to MQTT broker at {MQTT_BROKER_ADDRESS}:{MQTT_PORT}")
        # re-subscribe on every (re)connect, otherwise a broker restart
        # would silently stop all incoming data
        for topic in self.subscribed_topics:
            client.subscribe(topic)

    def on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties) -> None:
        self.is_connected = False
        logger.warning(f"Disconnected from MQTT broker: {reason_code}")

    def on_message(self, client, userdata, message) -> None:
        if self.on_message_callback is None:
            return
        try:
            payload = json.loads(message.payload.decode())
        except (json.JSONDecodeError, UnicodeDecodeError) as decode_error:
            logger.warning(f"Ignoring non-JSON payload on '{message.topic}': {decode_error}")
            return
        # This runs on paho's network thread. An exception that escapes here
        # ends that thread, and the whole interface silently stops receiving
        # -- so one bad message is logged and the next one is read.
        try:
            self.on_message_callback(message.topic, payload)
        except Exception:
            logger.exception(f"Handling a message on '{message.topic}' failed.")
