from typing import Callable


class MQTTSubscriber:
    """`client` is injected (duck-typed like paho.mqtt.client.Client) so
    this is testable with a fake that replays queued messages, no real
    broker needed.
    """

    def __init__(self, client, topic: str, qos: int = 1):
        self._client = client
        self._topic = topic
        self._qos = qos

    def run_forever(
        self,
        on_message: Callable[[bytes], None],
        on_connect: Callable[[], None] | None = None,
    ) -> None:
        def _on_connect(client, userdata, flags, rc, properties=None):
            client.subscribe(self._topic, qos=self._qos)
            if on_connect:
                on_connect()

        def _on_message(client, userdata, msg):
            on_message(msg.payload)

        self._client.on_connect = _on_connect
        self._client.on_message = _on_message
        self._client.loop_forever()
