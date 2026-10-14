"""Abstraction de transport vers les prototypes ESP32."""

import os
import json
from urllib.parse import urlparse
from abc import ABC, abstractmethod


class IoTTransport(ABC):
    @abstractmethod
    def publish_command(self, device_uid, command):
        raise NotImplementedError

    def subscribe_telemetry(self, handler):
        return None

    def subscribe_acknowledgements(self, handler):
        return None

    def get_connection_state(self, device_uid):
        return {"deviceUid": device_uid, "state": "unknown"}


class MockIoTTransport(IoTTransport):
    def publish_command(self, device_uid, command):
        return {
            "transport": "mock",
            "deviceUid": device_uid,
            "published": True,
            "commandUid": command.get("commandUid"),
        }

    def get_connection_state(self, device_uid):
        return {"deviceUid": device_uid, "state": "mock-ready"}


class HttpIoTTransport(IoTTransport):
    def publish_command(self, device_uid, command):
        endpoint = os.getenv("IOT_HTTP_SHARED_ENDPOINT")
        if not endpoint:
            raise RuntimeError("IOT_HTTP_SHARED_ENDPOINT non configure")
        import requests

        response = requests.post(endpoint, json=command, timeout=10)
        response.raise_for_status()
        return {"transport": "http", "deviceUid": device_uid, "published": True}


class MqttIoTTransport(IoTTransport):
    def publish_command(self, device_uid, command):
        import paho.mqtt.client as mqtt

        broker = os.getenv("MQTT_BROKER_URL", "").strip()
        if not broker:
            raise RuntimeError("MQTT_BROKER_URL non configure")
        parsed = urlparse(broker if "://" in broker else f"mqtts://{broker}")
        host = parsed.hostname
        port = parsed.port or (8883 if parsed.scheme == "mqtts" else 1883)
        if not host:
            raise RuntimeError("Adresse MQTT invalide")
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"argos-api-{os.getpid()}")
        username = os.getenv("MQTT_USERNAME", "")
        if username:
            client.username_pw_set(username, os.getenv("MQTT_PASSWORD", ""))
        if parsed.scheme == "mqtts":
            ca_path = os.getenv("MQTT_CA_CERT_PATH") or None
            client.tls_set(ca_certs=ca_path)
        client.connect(host, port, keepalive=30)
        client.loop_start()
        try:
            topic = f"argos/devices/{device_uid}/commands"
            info = client.publish(topic, json.dumps(command,separators=(",",":")), qos=1, retain=False)
            info.wait_for_publish(timeout=10)
            if info.rc != mqtt.MQTT_ERR_SUCCESS or not info.is_published():
                raise RuntimeError(f"Publication MQTT echouee ({info.rc})")
            return {"transport":"mqtt","deviceUid":device_uid,"published":True,
                    "commandUid":command.get("commandUid"),"topic":topic}
        finally:
            client.loop_stop()
            client.disconnect()

    def get_connection_state(self, device_uid):
        return {"deviceUid":device_uid,"state":"configured" if os.getenv("MQTT_BROKER_URL") else "not-configured"}


def build_transport():
    selected = (os.getenv("IOT_TRANSPORT") or "mock").lower()
    if selected == "http":
        return HttpIoTTransport()
    if selected == "mqtt":
        return MqttIoTTransport()
    return MockIoTTransport()
