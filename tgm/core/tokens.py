_CYRILLIC_CHARS_PER_TOKEN = 2.5
_OTHER_CHARS_PER_TOKEN = 3.0

_CYRILLIC_RANGE_START = "Ѐ"
_CYRILLIC_RANGE_END = "ԯ"


def estimate_tokens(text: str) -> int:
    cyrillic = 0
    other = 0
    for char in text:
        if _CYRILLIC_RANGE_START <= char <= _CYRILLIC_RANGE_END:
            cyrillic += 1
        else:
            other += 1
    return round(cyrillic / _CYRILLIC_CHARS_PER_TOKEN + other / _OTHER_CHARS_PER_TOKEN)
