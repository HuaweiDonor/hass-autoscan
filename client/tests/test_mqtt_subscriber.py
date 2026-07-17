from app.mqtt_subscriber import MQTTSubscriber


class FakeMsg:
    def __init__(self, topic, payload):
        self.topic = topic
        self.payload = payload


class FakeMQTTClient:
    def __init__(self, messages=None):
        self._messages = messages or []
        self.subscribed = []
        self.on_connect = None
        self.on_message = None

    def subscribe(self, topic, qos):
        self.subscribed.append((topic, qos))

    def loop_forever(self):
        if self.on_connect:
            self.on_connect(self, None, None, 0)
        for msg in self._messages:
            if self.on_message:
                self.on_message(self, None, msg)


def test_subscribes_to_configured_topic_on_connect():
    client = FakeMQTTClient()
    subscriber = MQTTSubscriber(client, topic="autoscan/plates/detections")

    subscriber.run_forever(on_message=lambda payload: None)

    assert client.subscribed == [("autoscan/plates/detections", 1)]


def test_invokes_handler_for_each_queued_message():
    client = FakeMQTTClient(
        messages=[
            FakeMsg("autoscan/plates/detections", b"payload1"),
            FakeMsg("autoscan/plates/detections", b"payload2"),
        ]
    )
    subscriber = MQTTSubscriber(client, topic="autoscan/plates/detections")
    received = []

    subscriber.run_forever(on_message=received.append)

    assert received == [b"payload1", b"payload2"]


def test_respects_custom_qos():
    client = FakeMQTTClient()
    subscriber = MQTTSubscriber(client, topic="t", qos=2)

    subscriber.run_forever(on_message=lambda payload: None)

    assert client.subscribed == [("t", 2)]


def test_invokes_extra_on_connect_hook_after_subscribing():
    client = FakeMQTTClient()
    subscriber = MQTTSubscriber(client, topic="autoscan/plates/detections")
    calls = []

    subscriber.run_forever(on_message=lambda payload: None, on_connect=lambda: calls.append(True))

    assert calls == [True]
    assert client.subscribed == [("autoscan/plates/detections", 1)]


def test_works_without_extra_on_connect_hook():
    client = FakeMQTTClient()
    subscriber = MQTTSubscriber(client, topic="t")

    subscriber.run_forever(on_message=lambda payload: None)  # should not raise
