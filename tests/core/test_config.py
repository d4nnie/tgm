import pytest

from tgm.core.config import (
    extract_telegram_credentials_from_config,
    extract_telegram_credentials_from_env,
    merge_telegram_credentials,
    merge_telegram_phone,
)
from tgm.core.types import TelegramCredentials


def test_extract_from_env_returns_credentials_when_both_set():
    env = {"TGM_API_ID": "12345", "TGM_API_HASH": "abcdef"}

    result = extract_telegram_credentials_from_env(env)

    assert result == TelegramCredentials(api_id=12345, api_hash="abcdef", phone=None)


def test_extract_from_env_returns_none_when_only_api_id():
    assert extract_telegram_credentials_from_env({"TGM_API_ID": "12345"}) is None


def test_extract_from_env_returns_none_when_only_api_hash():
    assert extract_telegram_credentials_from_env({"TGM_API_HASH": "abc"}) is None


def test_extract_from_env_returns_none_when_empty():
    assert extract_telegram_credentials_from_env({}) is None


def test_extract_from_env_treats_empty_strings_as_unset():
    env = {"TGM_API_ID": "", "TGM_API_HASH": ""}
    assert extract_telegram_credentials_from_env(env) is None


def test_extract_from_env_phone_is_always_none():
    env = {"TGM_API_ID": "1", "TGM_API_HASH": "h"}

    result = extract_telegram_credentials_from_env(env)

    assert result is not None
    assert result.phone is None


def test_extract_from_env_raises_on_non_numeric_api_id():
    env = {"TGM_API_ID": "not-a-number", "TGM_API_HASH": "h"}

    with pytest.raises(ValueError):
        extract_telegram_credentials_from_env(env)


def test_extract_from_config_returns_credentials_with_all_fields():
    config = {"telegram": {"api_id": 1, "api_hash": "h", "phone": "+1"}}

    result = extract_telegram_credentials_from_config(config)

    assert result == TelegramCredentials(api_id=1, api_hash="h", phone="+1")


def test_extract_from_config_returns_credentials_without_phone():
    config = {"telegram": {"api_id": 1, "api_hash": "h"}}

    result = extract_telegram_credentials_from_config(config)

    assert result == TelegramCredentials(api_id=1, api_hash="h", phone=None)


def test_extract_from_config_returns_none_when_telegram_section_missing():
    assert extract_telegram_credentials_from_config({}) is None


def test_extract_from_config_returns_none_when_telegram_section_empty():
    assert extract_telegram_credentials_from_config({"telegram": {}}) is None


def test_extract_from_config_returns_none_when_telegram_section_is_none():
    assert extract_telegram_credentials_from_config({"telegram": None}) is None


def test_extract_from_config_returns_none_when_only_api_id():
    assert extract_telegram_credentials_from_config({"telegram": {"api_id": 1}}) is None


def test_extract_from_config_coerces_string_api_id_to_int():
    config = {"telegram": {"api_id": "42", "api_hash": "h"}}

    result = extract_telegram_credentials_from_config(config)

    assert result is not None
    assert result.api_id == 42
    assert isinstance(result.api_id, int)


def test_extract_from_config_ignores_unrelated_sections():
    config = {"general": {"theme": "dark"}, "telegram": {"api_id": 1, "api_hash": "h"}}

    result = extract_telegram_credentials_from_config(config)

    assert result == TelegramCredentials(api_id=1, api_hash="h", phone=None)


def test_merge_credentials_writes_all_fields_when_phone_present():
    credentials = TelegramCredentials(api_id=1, api_hash="h", phone="+1")

    result = merge_telegram_credentials({}, credentials)

    assert result == {"telegram": {"api_id": 1, "api_hash": "h", "phone": "+1"}}


def test_merge_credentials_skips_phone_when_none():
    credentials = TelegramCredentials(api_id=1, api_hash="h", phone=None)

    result = merge_telegram_credentials({}, credentials)

    assert result == {"telegram": {"api_id": 1, "api_hash": "h"}}


def test_merge_credentials_preserves_other_sections():
    config = {"general": {"theme": "dark"}, "ui": {"compact": True}}
    credentials = TelegramCredentials(api_id=1, api_hash="h", phone=None)

    result = merge_telegram_credentials(config, credentials)

    assert result["general"] == {"theme": "dark"}
    assert result["ui"] == {"compact": True}


def test_merge_credentials_preserves_unknown_telegram_keys():
    config = {"telegram": {"phone": "+0", "experimental_flag": True}}
    credentials = TelegramCredentials(api_id=1, api_hash="h", phone=None)

    result = merge_telegram_credentials(config, credentials)

    assert result["telegram"]["experimental_flag"] is True
    assert result["telegram"]["phone"] == "+0"
    assert result["telegram"]["api_id"] == 1
    assert result["telegram"]["api_hash"] == "h"


def test_merge_credentials_overwrites_existing():
    config = {"telegram": {"api_id": 1, "api_hash": "old", "phone": "+0"}}
    credentials = TelegramCredentials(api_id=2, api_hash="new", phone="+1")

    result = merge_telegram_credentials(config, credentials)

    assert result["telegram"] == {"api_id": 2, "api_hash": "new", "phone": "+1"}


def test_merge_credentials_does_not_mutate_input():
    config = {"telegram": {"api_id": 1, "api_hash": "old"}, "other": {"key": "value"}}
    credentials = TelegramCredentials(api_id=2, api_hash="new", phone=None)

    merge_telegram_credentials(config, credentials)

    assert config == {"telegram": {"api_id": 1, "api_hash": "old"}, "other": {"key": "value"}}


def test_merge_phone_adds_to_empty_config():
    result = merge_telegram_phone({}, "+1")

    assert result == {"telegram": {"phone": "+1"}}


def test_merge_phone_preserves_existing_api_credentials():
    config = {"telegram": {"api_id": 1, "api_hash": "h"}}

    result = merge_telegram_phone(config, "+1")

    assert result["telegram"] == {"api_id": 1, "api_hash": "h", "phone": "+1"}


def test_merge_phone_overwrites_existing():
    config = {"telegram": {"api_id": 1, "api_hash": "h", "phone": "+0"}}

    result = merge_telegram_phone(config, "+1")

    assert result["telegram"]["phone"] == "+1"


def test_merge_phone_preserves_other_sections():
    config = {"general": {"theme": "dark"}}

    result = merge_telegram_phone(config, "+1")

    assert result["general"] == {"theme": "dark"}
    assert result["telegram"] == {"phone": "+1"}


def test_merge_phone_does_not_mutate_input():
    config = {"telegram": {"api_id": 1, "api_hash": "h"}}

    merge_telegram_phone(config, "+1")

    assert config == {"telegram": {"api_id": 1, "api_hash": "h"}}
