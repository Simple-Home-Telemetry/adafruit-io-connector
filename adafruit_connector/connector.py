import datetime
import json
import os

import paho.mqtt.client as mqtt
import requests
from Adafruit_IO import Client, Feed, RequestError

ADAFRUIT_USER = os.environ.get("ADAFRUIT_IO_USER")
ADAFRUIT_KEY = os.environ.get("ADAFRUIT_IO_KEY")

MQTT_BROKER = os.environ.get("MQTT_BROKER", "broker.hivemq.com")
MQTT_BROKER_PORT = int(os.environ.get("MQTT_BROKER_PORT", 1883))
MQTT_BROKER_USER = os.environ.get("MQTT_BROKER_USER")
MQTT_BROKER_PASSWORD = os.environ.get("MQTT_BROKER_PASSWORD")
MQTT_TOPIC_BASE = os.environ.get("MQTT_TOPIC_BASE", "geo-milev-home")

ALLOWED_IDS_LIST = list(
    filter(
        lambda var: var != "", os.environ.get("ALLOWED_IDS", "vasko-room:").split(":")
    )
)

MQTT_TOPIC_TEMPERATURE = f"{MQTT_TOPIC_BASE}/+/temperature"
MQTT_TOPIC_HUMIDITY = f"{MQTT_TOPIC_BASE}/+/humidity"


aio = Client(ADAFRUIT_USER, ADAFRUIT_KEY)

temperature_feeds_dict = {}
for feed_id in ALLOWED_IDS_LIST:
    try:
        temperature_feed = aio.feeds(f"{feed_id}-temperature")
    except RequestError:
        feed = Feed(name=f"{feed_id}-temperature")
        temperature_feed = aio.create_feed(feed)
    temperature_feeds_dict[f"{feed_id}-temperature"] = temperature_feed

humidity_feeds_dict = {}
for feed_id in ALLOWED_IDS_LIST:
    try:
        humidity_feed = aio.feeds(f"{feed_id}-humidity")
    except RequestError:
        feed = Feed(name=f"{feed_id}-humidity")
        humidity_feed = aio.create_feed(feed)
    humidity_feeds_dict[f"{feed_id}-humidity"] = humidity_feed


def publish_datapoint(feed_id, datapoint, timestamp):
    timezone = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo
    timestamp = datetime.datetime.fromtimestamp(timestamp, tz=timezone)
    url = (
        "https://io.adafruit.com/api/v2/"
        + ADAFRUIT_USER
        + "/feeds/"
        + feed_id
        + "/data"
    )

    body = {"value": datapoint, "created_at": timestamp.isoformat()}
    headers = {"X-AIO-Key": ADAFRUIT_KEY, "Content-Type": "application/json"}
    try:
        r = requests.post(url, json=body, headers=headers)
        print(r.text)
    except Exception as e:
        print(e)


def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe(MQTT_TOPIC_TEMPERATURE)
    client.subscribe(MQTT_TOPIC_HUMIDITY)


def push_temperature(feed_id, msg):
    message_dict = json.loads(msg.payload.decode("utf-8"))
    payload = message_dict["payload"]
    temperature = payload["tempC"]
    timestamp = int(payload["timestamp"])
    publish_datapoint(feed_id, temperature, timestamp)


def push_humidity(feed_id, msg):
    message_dict = json.loads(msg.payload.decode("utf-8"))
    payload = message_dict["payload"]
    temperature = payload["relHumidity"]
    timestamp = int(payload["timestamp"])
    publish_datapoint(feed_id, temperature, timestamp)


def on_message(client, userdata, msg):
    topic_parts = msg.topic.split("/")

    if topic_parts[1] not in ALLOWED_IDS_LIST:
        return

    if topic_parts[2] == "temperature":
        push_temperature(f"{topic_parts[1]}-temperature", msg)

    if topic_parts[2] == "humidity":
        push_humidity(f"{topic_parts[1]}-humidity", msg)


def main():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_BROKER, MQTT_BROKER_PORT, 60)
    client.username_pw_set(MQTT_BROKER_USER, MQTT_BROKER_PASSWORD)

    client.loop_forever()
