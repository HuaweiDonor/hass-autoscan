from app.normalize import normalize_plate


class Whitelist:
    def __init__(self, plates):
        self._plates = {normalize_plate(p) for p in plates}

    def is_allowed(self, plate_text: str) -> bool:
        return normalize_plate(plate_text) in self._plates
