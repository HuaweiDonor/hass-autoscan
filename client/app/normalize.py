import re

# Cyrillic letters used on Russian/CIS plates, mapped to their visually
# identical Latin equivalent per GOST R 50577 transliteration.
_CYRILLIC_TO_LATIN = {
    "А": "A",
    "В": "B",
    "Е": "E",
    "К": "K",
    "М": "M",
    "Н": "H",
    "О": "O",
    "Р": "P",
    "С": "C",
    "Т": "T",
    "У": "Y",
    "Х": "X",
}

_STRIP_RE = re.compile(r"[\s\-]+")


def normalize_plate(text: str) -> str:
    text = _STRIP_RE.sub("", text.upper())
    return "".join(_CYRILLIC_TO_LATIN.get(ch, ch) for ch in text)
