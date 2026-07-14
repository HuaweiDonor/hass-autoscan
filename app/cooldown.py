import time


class CooldownManager:
    def __init__(self, cooldown_seconds: float, clock=time.time):
        self._cooldown_seconds = cooldown_seconds
        self._clock = clock
        self._last_trigger: dict[str, float] = {}

    def should_trigger(self, plate: str) -> bool:
        now = self._clock()
        last = self._last_trigger.get(plate)
        if last is not None and now - last < self._cooldown_seconds:
            return False
        self._last_trigger[plate] = now
        return True
