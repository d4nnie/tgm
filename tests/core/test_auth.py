from dataclasses import replace

from tgm.core.auth import (
    ApiCredentialsProvided,
    AuthorizationChecked,
    CheckAuthorization,
    CodeRequested,
    CredentialsLoaded,
    CredentialsPersisted,
    Finish,
    LoadCredentials,
    PasswordProvided,
    PasswordSignInCompleted,
    PersistFullCredentials,
    PersistPhone,
    PhoneProvided,
    RequestApiCredentials,
    RequestCode,
    RequestPassword,
    RequestPhone,
    RequestSmsCode,
    RestrictSession,
    SessionRestricted,
    SignInCompleted,
    SignInWithCode,
    SignInWithPassword,
    SmsCodeProvided,
    apply_event,
    create_initial_state,
    decide_next_action,
)
from tgm.core.types import TelegramCredentials


def _full_credentials() -> TelegramCredentials:
    return TelegramCredentials(api_id=12345, api_hash="hash", phone="+1")


def _api_only_credentials() -> TelegramCredentials:
    return TelegramCredentials(api_id=12345, api_hash="hash", phone=None)


def test_initial_state_has_no_progress():
    state = create_initial_state()

    assert state.credentials is None
    assert state.fresh_api_credentials is False
    assert state.fresh_phone is False
    assert state.credentials_load_attempted is False
    assert state.authorization_checked is False
    assert state.persisted is False


def test_decide_starts_with_load_credentials():
    assert decide_next_action(create_initial_state()) == LoadCredentials()


def test_decide_requests_api_credentials_after_empty_load():
    state = replace(create_initial_state(), credentials_load_attempted=True)

    assert decide_next_action(state) == RequestApiCredentials()


def test_decide_requests_phone_when_phone_missing():
    state = replace(
        create_initial_state(),
        credentials_load_attempted=True,
        credentials=_api_only_credentials(),
    )

    assert decide_next_action(state) == RequestPhone()


def test_decide_checks_authorization_when_full_credentials():
    credentials = _full_credentials()
    state = replace(create_initial_state(), credentials_load_attempted=True, credentials=credentials)

    assert decide_next_action(state) == CheckAuthorization(credentials)


def test_decide_restricts_session_before_finish_for_already_authorized_user():
    credentials = _full_credentials()
    state = replace(
        create_initial_state(),
        credentials_load_attempted=True,
        credentials=credentials,
        authorization_checked=True,
        authorized=True,
    )

    assert decide_next_action(state) == RestrictSession()


def test_decide_finishes_after_already_authorized_session_restricted():
    credentials = _full_credentials()
    state = replace(
        create_initial_state(),
        credentials_load_attempted=True,
        credentials=credentials,
        authorization_checked=True,
        authorized=True,
        session_restricted=True,
    )

    assert decide_next_action(state) == Finish(credentials)


def test_decide_requests_code_when_unauthorized():
    credentials = _full_credentials()
    state = replace(
        create_initial_state(),
        credentials_load_attempted=True,
        credentials=credentials,
        authorization_checked=True,
        authorized=False,
    )

    assert decide_next_action(state) == RequestCode("+1")


def test_decide_requests_sms_code_after_code_sent():
    credentials = _full_credentials()
    state = replace(
        create_initial_state(),
        credentials_load_attempted=True,
        credentials=credentials,
        authorization_checked=True,
        authorized=False,
        code_request_sent=True,
    )

    assert decide_next_action(state) == RequestSmsCode()


def test_decide_signs_in_with_code_after_sms_provided():
    credentials = _full_credentials()
    state = replace(
        create_initial_state(),
        credentials_load_attempted=True,
        credentials=credentials,
        authorization_checked=True,
        authorized=False,
        code_request_sent=True,
        sms_code="11111",
    )

    assert decide_next_action(state) == SignInWithCode("+1", "11111")


def test_decide_requests_password_when_required_and_missing():
    credentials = _full_credentials()
    state = replace(
        create_initial_state(),
        credentials_load_attempted=True,
        credentials=credentials,
        authorization_checked=True,
        authorized=False,
        code_request_sent=True,
        sms_code="11111",
        sign_in_attempted=True,
        password_required=True,
    )

    assert decide_next_action(state) == RequestPassword()


def test_decide_signs_in_with_password_after_password_provided():
    credentials = _full_credentials()
    state = replace(
        create_initial_state(),
        credentials_load_attempted=True,
        credentials=credentials,
        authorization_checked=True,
        authorized=False,
        code_request_sent=True,
        sms_code="11111",
        sign_in_attempted=True,
        password_required=True,
        password="secret",
    )

    assert decide_next_action(state) == SignInWithPassword("secret")


def test_decide_restricts_session_after_password_sign_in():
    credentials = _full_credentials()
    state = replace(
        create_initial_state(),
        credentials_load_attempted=True,
        credentials=credentials,
        authorization_checked=True,
        authorized=False,
        code_request_sent=True,
        sms_code="11111",
        sign_in_attempted=True,
        password_required=True,
        password="secret",
        password_sign_in_attempted=True,
    )

    assert decide_next_action(state) == RestrictSession()


def test_decide_restricts_session_when_no_password_needed():
    credentials = _full_credentials()
    state = replace(
        create_initial_state(),
        credentials_load_attempted=True,
        credentials=credentials,
        authorization_checked=True,
        authorized=False,
        code_request_sent=True,
        sms_code="11111",
        sign_in_attempted=True,
        password_required=False,
    )

    assert decide_next_action(state) == RestrictSession()


def test_decide_persists_full_credentials_when_fresh_api():
    credentials = _full_credentials()
    state = replace(
        create_initial_state(),
        credentials_load_attempted=True,
        credentials=credentials,
        fresh_api_credentials=True,
        fresh_phone=True,
        authorization_checked=True,
        authorized=False,
        code_request_sent=True,
        sms_code="11111",
        sign_in_attempted=True,
        session_restricted=True,
    )

    assert decide_next_action(state) == PersistFullCredentials(credentials)


def test_decide_persists_phone_only_when_fresh_phone_without_fresh_api():
    credentials = _full_credentials()
    state = replace(
        create_initial_state(),
        credentials_load_attempted=True,
        credentials=credentials,
        fresh_api_credentials=False,
        fresh_phone=True,
        authorization_checked=True,
        authorized=False,
        code_request_sent=True,
        sms_code="11111",
        sign_in_attempted=True,
        session_restricted=True,
    )

    assert decide_next_action(state) == PersistPhone("+1")


def test_decide_skips_persistence_when_no_fresh_data():
    credentials = _full_credentials()
    state = replace(
        create_initial_state(),
        credentials_load_attempted=True,
        credentials=credentials,
        authorization_checked=True,
        authorized=False,
        code_request_sent=True,
        sms_code="11111",
        sign_in_attempted=True,
        session_restricted=True,
    )

    assert decide_next_action(state) == Finish(credentials)


def test_decide_finishes_after_persistence():
    credentials = _full_credentials()
    state = replace(
        create_initial_state(),
        credentials_load_attempted=True,
        credentials=credentials,
        fresh_api_credentials=True,
        authorization_checked=True,
        authorized=False,
        code_request_sent=True,
        sms_code="11111",
        sign_in_attempted=True,
        session_restricted=True,
        persisted=True,
    )

    assert decide_next_action(state) == Finish(credentials)


def test_apply_credentials_loaded_with_none_marks_attempted():
    state = apply_event(create_initial_state(), CredentialsLoaded(None))

    assert state.credentials_load_attempted is True
    assert state.credentials is None


def test_apply_credentials_loaded_with_credentials_sets_them():
    credentials = _full_credentials()

    state = apply_event(create_initial_state(), CredentialsLoaded(credentials))

    assert state.credentials_load_attempted is True
    assert state.credentials == credentials


def test_apply_api_credentials_provided_marks_fresh():
    state = replace(create_initial_state(), credentials_load_attempted=True)

    new_state = apply_event(state, ApiCredentialsProvided(api_id=42, api_hash="h"))

    assert new_state.credentials == TelegramCredentials(api_id=42, api_hash="h", phone=None)
    assert new_state.fresh_api_credentials is True
    assert new_state.fresh_phone is False


def test_apply_phone_provided_extends_credentials():
    state = replace(
        create_initial_state(),
        credentials_load_attempted=True,
        credentials=_api_only_credentials(),
    )

    new_state = apply_event(state, PhoneProvided("+1"))

    assert new_state.credentials == TelegramCredentials(api_id=12345, api_hash="hash", phone="+1")
    assert new_state.fresh_phone is True


def test_apply_authorization_checked_records_result():
    state = replace(
        create_initial_state(),
        credentials_load_attempted=True,
        credentials=_full_credentials(),
    )

    authorized_state = apply_event(state, AuthorizationChecked(True))
    unauthorized_state = apply_event(state, AuthorizationChecked(False))

    assert authorized_state.authorization_checked is True
    assert authorized_state.authorized is True
    assert unauthorized_state.authorization_checked is True
    assert unauthorized_state.authorized is False


def test_apply_code_requested_marks_sent():
    state = apply_event(create_initial_state(), CodeRequested())

    assert state.code_request_sent is True


def test_apply_sms_code_provided_stores_code():
    state = apply_event(create_initial_state(), SmsCodeProvided("11111"))

    assert state.sms_code == "11111"


def test_apply_sign_in_completed_records_password_requirement():
    requires_password = apply_event(create_initial_state(), SignInCompleted(password_required=True))
    no_password = apply_event(create_initial_state(), SignInCompleted(password_required=False))

    assert requires_password.sign_in_attempted is True
    assert requires_password.password_required is True
    assert no_password.sign_in_attempted is True
    assert no_password.password_required is False


def test_apply_password_provided_stores_password():
    state = apply_event(create_initial_state(), PasswordProvided("secret"))

    assert state.password == "secret"


def test_apply_password_sign_in_completed_marks_attempted():
    state = apply_event(create_initial_state(), PasswordSignInCompleted())

    assert state.password_sign_in_attempted is True


def test_apply_session_restricted_marks_restricted():
    state = apply_event(create_initial_state(), SessionRestricted())

    assert state.session_restricted is True


def test_apply_credentials_persisted_marks_persisted():
    state = apply_event(create_initial_state(), CredentialsPersisted())

    assert state.persisted is True


def test_apply_does_not_mutate_input_state():
    state = create_initial_state()

    apply_event(state, CredentialsLoaded(_full_credentials()))

    assert state == create_initial_state()


def test_full_flow_fresh_user_without_2fa():
    state = create_initial_state()
    expected_credentials = TelegramCredentials(api_id=12345, api_hash="hash", phone="+1")

    assert decide_next_action(state) == LoadCredentials()
    state = apply_event(state, CredentialsLoaded(None))

    assert decide_next_action(state) == RequestApiCredentials()
    state = apply_event(state, ApiCredentialsProvided(api_id=12345, api_hash="hash"))

    assert decide_next_action(state) == RequestPhone()
    state = apply_event(state, PhoneProvided("+1"))

    assert decide_next_action(state) == CheckAuthorization(expected_credentials)
    state = apply_event(state, AuthorizationChecked(False))

    assert decide_next_action(state) == RequestCode("+1")
    state = apply_event(state, CodeRequested())

    assert decide_next_action(state) == RequestSmsCode()
    state = apply_event(state, SmsCodeProvided("11111"))

    assert decide_next_action(state) == SignInWithCode("+1", "11111")
    state = apply_event(state, SignInCompleted(password_required=False))

    assert decide_next_action(state) == PersistFullCredentials(expected_credentials)
    state = apply_event(state, CredentialsPersisted())

    assert decide_next_action(state) == RestrictSession()
    state = apply_event(state, SessionRestricted())

    assert decide_next_action(state) == Finish(expected_credentials)


def test_full_flow_fresh_user_with_2fa():
    state = create_initial_state()
    expected_credentials = TelegramCredentials(api_id=42, api_hash="h", phone="+1")

    state = apply_event(state, CredentialsLoaded(None))
    state = apply_event(state, ApiCredentialsProvided(api_id=42, api_hash="h"))
    state = apply_event(state, PhoneProvided("+1"))
    state = apply_event(state, AuthorizationChecked(False))
    state = apply_event(state, CodeRequested())
    state = apply_event(state, SmsCodeProvided("22222"))

    assert decide_next_action(state) == SignInWithCode("+1", "22222")
    state = apply_event(state, SignInCompleted(password_required=True))

    assert decide_next_action(state) == RequestPassword()
    state = apply_event(state, PasswordProvided("secret"))

    assert decide_next_action(state) == SignInWithPassword("secret")
    state = apply_event(state, PasswordSignInCompleted())

    assert decide_next_action(state) == PersistFullCredentials(expected_credentials)
    state = apply_event(state, CredentialsPersisted())

    assert decide_next_action(state) == RestrictSession()
    state = apply_event(state, SessionRestricted())

    assert decide_next_action(state) == Finish(expected_credentials)


def test_full_flow_existing_valid_session():
    state = create_initial_state()
    loaded_credentials = _full_credentials()

    assert decide_next_action(state) == LoadCredentials()
    state = apply_event(state, CredentialsLoaded(loaded_credentials))

    assert decide_next_action(state) == CheckAuthorization(loaded_credentials)
    state = apply_event(state, AuthorizationChecked(True))

    assert decide_next_action(state) == RestrictSession()
    state = apply_event(state, SessionRestricted())

    assert decide_next_action(state) == Finish(loaded_credentials)


def test_full_flow_env_credentials_need_phone_only():
    state = create_initial_state()
    env_credentials = _api_only_credentials()
    expected_credentials = TelegramCredentials(api_id=12345, api_hash="hash", phone="+9")

    state = apply_event(state, CredentialsLoaded(env_credentials))

    assert decide_next_action(state) == RequestPhone()
    state = apply_event(state, PhoneProvided("+9"))
    state = apply_event(state, AuthorizationChecked(False))
    state = apply_event(state, CodeRequested())
    state = apply_event(state, SmsCodeProvided("33333"))
    state = apply_event(state, SignInCompleted(password_required=False))

    assert decide_next_action(state) == PersistPhone("+9")
    state = apply_event(state, CredentialsPersisted())

    assert decide_next_action(state) == RestrictSession()
    state = apply_event(state, SessionRestricted())

    assert decide_next_action(state) == Finish(expected_credentials)
