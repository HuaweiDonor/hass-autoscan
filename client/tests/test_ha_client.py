import requests

from app.ha_client import HAClient


def make_client(**overrides):
    defaults = dict(
        base_url="http://homeassistant.local:8123",
        token="secret-token",
        domain="switch",
        service="turn_on",
        entity_id="switch.gate_relay",
        max_retries=3,
        sleep=lambda seconds: None,
    )
    defaults.update(overrides)
    return HAClient(**defaults)


def test_calls_ha_service_with_correct_url_and_payload(requests_mock):
    requests_mock.post(
        "http://homeassistant.local:8123/api/services/switch/turn_on",
        json={},
        status_code=200,
    )
    client = make_client()

    result = client.call_gate()

    assert result is True
    assert requests_mock.call_count == 1
    request = requests_mock.request_history[0]
    assert request.headers["Authorization"] == "Bearer secret-token"
    assert request.json() == {"entity_id": "switch.gate_relay"}


def test_retries_on_failure_and_succeeds(requests_mock):
    requests_mock.post(
        "http://homeassistant.local:8123/api/services/switch/turn_on",
        [
            {"status_code": 500},
            {"status_code": 500},
            {"json": {}, "status_code": 200},
        ],
    )
    client = make_client()

    result = client.call_gate()

    assert result is True
    assert requests_mock.call_count == 3


def test_returns_false_after_exhausting_retries(requests_mock):
    requests_mock.post(
        "http://homeassistant.local:8123/api/services/switch/turn_on",
        status_code=500,
    )
    client = make_client(max_retries=3)

    result = client.call_gate()

    assert result is False
    assert requests_mock.call_count == 3


def test_does_not_raise_on_connection_error(requests_mock):
    requests_mock.post(
        "http://homeassistant.local:8123/api/services/switch/turn_on",
        exc=requests.ConnectionError,
    )
    client = make_client(max_retries=2)

    result = client.call_gate()

    assert result is False
    assert requests_mock.call_count == 2
