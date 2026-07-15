import logging
import time

import requests

logger = logging.getLogger(__name__)


class HAClient:
    def __init__(
        self,
        base_url: str,
        token: str,
        domain: str,
        service: str,
        entity_id: str,
        max_retries: int = 3,
        backoff_seconds: float = 1.0,
        sleep=time.sleep,
    ):
        self._url = f"{base_url.rstrip('/')}/api/services/{domain}/{service}"
        self._headers = {"Authorization": f"Bearer {token}"}
        self._entity_id = entity_id
        self._max_retries = max_retries
        self._backoff_seconds = backoff_seconds
        self._sleep = sleep

    def call_gate(self) -> bool:
        for attempt in range(1, self._max_retries + 1):
            try:
                response = requests.post(
                    self._url,
                    headers=self._headers,
                    json={"entity_id": self._entity_id},
                    timeout=10,
                )
                if response.ok:
                    return True
                logger.warning(
                    "HA call failed (attempt %d/%d): status=%s",
                    attempt,
                    self._max_retries,
                    response.status_code,
                )
            except requests.RequestException as exc:
                logger.warning(
                    "HA call failed (attempt %d/%d): %s",
                    attempt,
                    self._max_retries,
                    exc,
                )

            if attempt < self._max_retries:
                self._sleep(self._backoff_seconds)

        logger.error("HA call exhausted %d retries, giving up", self._max_retries)
        return False
