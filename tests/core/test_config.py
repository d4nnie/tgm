import pytest

from tgm.core.config import (
    DEFAULT_LLM_CONFIG_SECTION,
    extract_llm_provider_config_from_config,
    extract_telegram_credentials_from_config,
    extract_telegram_credentials_from_env,
    merge_telegram_credentials,
    merge_telegram_phone,
    validate_base_url,
)
from tgm.core.types import LlmProviderConfig, TelegramCredentials


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


def _full_llm_section(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "provider": "openai-compat",
        "base_url": "http://127.0.0.1:11434/v1",
        "model": "gpt-oss:20b",
        "api_key_env": "OPENAI_API_KEY",
        "options": {"num_ctx": 24576},
    }
    base.update(overrides)
    return base


def test_extract_llm_provider_config_returns_openai_compat_with_full_section():
    config = {"llm": _full_llm_section()}

    result = extract_llm_provider_config_from_config(config)

    assert result == LlmProviderConfig(
        provider="openai-compat",
        base_url="http://127.0.0.1:11434/v1",
        model="gpt-oss:20b",
        api_key_env="OPENAI_API_KEY",
        options={"num_ctx": 24576},
    )


def test_extract_llm_provider_config_rejects_anthropic_value_with_explainable_message():
    config = {"llm": _full_llm_section(provider="anthropic")}

    with pytest.raises(ValueError, match="reserved for a future release"):
        extract_llm_provider_config_from_config(config)


def test_extract_llm_provider_config_omits_optional_api_key_env():
    section = _full_llm_section()
    del section["api_key_env"]

    result = extract_llm_provider_config_from_config({"llm": section})

    assert result.api_key_env is None


def test_extract_llm_provider_config_omits_optional_options():
    section = _full_llm_section()
    del section["options"]

    result = extract_llm_provider_config_from_config({"llm": section})

    assert result.options is None


def test_extract_llm_provider_config_treats_empty_string_api_key_env_as_none():
    config = {"llm": _full_llm_section(api_key_env="")}

    result = extract_llm_provider_config_from_config(config)

    assert result.api_key_env is None


def test_extract_llm_provider_config_rejects_non_string_api_key_env():
    config = {"llm": _full_llm_section(api_key_env=42)}

    with pytest.raises(ValueError, match=r"llm\.api_key_env"):
        extract_llm_provider_config_from_config(config)


def test_extract_llm_provider_config_raises_when_section_missing():
    with pytest.raises(ValueError, match=r"\[llm\]"):
        extract_llm_provider_config_from_config({})


def test_extract_llm_provider_config_raises_when_provider_unknown():
    config = {"llm": _full_llm_section(provider="bogus")}

    with pytest.raises(ValueError, match=r"llm\.provider"):
        extract_llm_provider_config_from_config(config)


def test_extract_llm_provider_config_raises_when_base_url_missing():
    section = _full_llm_section()
    del section["base_url"]

    with pytest.raises(ValueError, match=r"llm\.base_url"):
        extract_llm_provider_config_from_config({"llm": section})


def test_extract_llm_provider_config_raises_when_base_url_empty():
    config = {"llm": _full_llm_section(base_url="")}

    with pytest.raises(ValueError, match=r"llm\.base_url"):
        extract_llm_provider_config_from_config(config)


def test_extract_llm_provider_config_raises_when_model_missing():
    section = _full_llm_section()
    del section["model"]

    with pytest.raises(ValueError, match=r"llm\.model"):
        extract_llm_provider_config_from_config({"llm": section})


def test_extract_llm_provider_config_raises_when_options_not_a_table():
    config = {"llm": _full_llm_section(options=42)}

    with pytest.raises(ValueError, match=r"llm\.options"):
        extract_llm_provider_config_from_config(config)


def test_default_llm_config_section_parses_back_to_local_ollama_preset():
    result = extract_llm_provider_config_from_config({"llm": DEFAULT_LLM_CONFIG_SECTION})

    assert result == LlmProviderConfig(
        provider="openai-compat",
        base_url="http://127.0.0.1:11434/v1",
        model="gpt-oss:20b",
        api_key_env=None,
        options={"num_ctx": 24576},
        allow_hosts=(),
    )


def test_validate_base_url_accepts_loopback_http():
    validate_base_url("http://127.0.0.1:11434/v1", [])


def test_validate_base_url_accepts_localhost():
    validate_base_url("http://localhost:11434/v1", [])


def test_validate_base_url_accepts_ipv6_loopback():
    validate_base_url("http://[::1]:11434/v1", [])


def test_validate_base_url_accepts_https_host_in_allow_list():
    validate_base_url("https://api.openai.com/v1", ["api.openai.com"])


def test_validate_base_url_rejects_non_loopback_without_allow_list():
    with pytest.raises(ValueError, match="allow-list"):
        validate_base_url("https://api.openai.com/v1", [])


def test_validate_base_url_rejects_http_non_loopback():
    with pytest.raises(ValueError, match="https"):
        validate_base_url("http://api.openai.com/v1", ["api.openai.com"])


def test_validate_base_url_rejects_host_not_in_allow_list():
    with pytest.raises(ValueError, match="allow-list"):
        validate_base_url("https://attacker.example/v1", ["api.openai.com"])


def test_validate_base_url_rejects_empty_url():
    with pytest.raises(ValueError, match="non-empty"):
        validate_base_url("", [])


def test_validate_base_url_rejects_non_http_scheme():
    with pytest.raises(ValueError, match="scheme"):
        validate_base_url("ftp://127.0.0.1/x", [])


def test_extract_llm_provider_config_validates_base_url_against_allow_hosts():
    config = {"llm": _full_llm_section(base_url="https://attacker.example/v1")}

    with pytest.raises(ValueError, match="allow-list"):
        extract_llm_provider_config_from_config(config)


def test_extract_llm_provider_config_accepts_https_host_with_allow_hosts():
    section = _full_llm_section(base_url="https://api.openai.com/v1")
    section["allow_hosts"] = ["api.openai.com"]

    result = extract_llm_provider_config_from_config({"llm": section})

    assert result.base_url == "https://api.openai.com/v1"
    assert result.allow_hosts == ("api.openai.com",)


def test_extract_llm_provider_config_rejects_non_list_allow_hosts():
    section = _full_llm_section()
    section["allow_hosts"] = "api.openai.com"

    with pytest.raises(ValueError, match="allow_hosts"):
        extract_llm_provider_config_from_config({"llm": section})
