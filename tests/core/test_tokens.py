from tgm.core.tokens import estimate_tokens


def test_estimate_tokens_empty_returns_zero():
    assert estimate_tokens("") == 0


def test_estimate_tokens_pure_latin_uses_three_chars_per_token():
    text = "The quick brown fox jumps over the lazy dog"

    assert estimate_tokens(text) == round(len(text) / 3)


def test_estimate_tokens_pure_cyrillic_uses_two_and_a_half_chars_per_token():
    text = "Съешьещёэтихмягкихфранцузскихбулокдавыпейчаю"

    assert estimate_tokens(text) == round(len(text) / 2.5)


def test_estimate_tokens_handles_yo_letter():
    text = "ёЁ"

    assert estimate_tokens(text) == round(2 / 2.5)


def test_estimate_tokens_mixed_falls_between_pure_estimates():
    text = "Hello мир, how are you? Как дела сегодня?"
    pure_latin_estimate = round(len(text) / 3)
    pure_cyrillic_estimate = round(len(text) / 2.5)

    actual = estimate_tokens(text)

    assert pure_latin_estimate <= actual <= pure_cyrillic_estimate


def test_estimate_tokens_treats_digits_and_punctuation_as_other():
    text = "42 messages, 7 chats."

    assert estimate_tokens(text) == round(len(text) / 3)


def test_estimate_tokens_within_fifteen_percent_for_reference_corpus():
    cases = [
        ("a" * 30, 10),
        ("я" * 25, 10),
        ("a" * 12 + "я" * 10, 8),
    ]
    for text, expected in cases:
        actual = estimate_tokens(text)
        delta = abs(actual - expected) / expected
        assert delta <= 0.15, f"text={text!r} actual={actual} expected={expected} delta={delta:.2%}"
