from dataclasses import dataclass, replace

from tgm.core.types import TelegramCredentials


class AuthorizationFlowError(RuntimeError):
    pass


@dataclass(frozen=True)
class AuthorizationState:
    credentials: TelegramCredentials | None = None
    fresh_api_credentials: bool = False
    fresh_phone: bool = False
    credentials_load_attempted: bool = False
    authorization_checked: bool = False
    authorized: bool = False
    code_request_sent: bool = False
    sms_code: str | None = None
    sign_in_attempted: bool = False
    password_required: bool = False
    password: str | None = None
    password_sign_in_attempted: bool = False
    session_restricted: bool = False
    persisted: bool = False


@dataclass(frozen=True)
class LoadCredentials:
    pass


@dataclass(frozen=True)
class RequestApiCredentials:
    pass


@dataclass(frozen=True)
class RequestPhone:
    pass


@dataclass(frozen=True)
class CheckAuthorization:
    credentials: TelegramCredentials


@dataclass(frozen=True)
class RequestCode:
    phone: str


@dataclass(frozen=True)
class RequestSmsCode:
    pass


@dataclass(frozen=True)
class SignInWithCode:
    phone: str
    code: str


@dataclass(frozen=True)
class RequestPassword:
    pass


@dataclass(frozen=True)
class SignInWithPassword:
    password: str


@dataclass(frozen=True)
class RestrictSession:
    pass


@dataclass(frozen=True)
class PersistFullCredentials:
    credentials: TelegramCredentials


@dataclass(frozen=True)
class PersistPhone:
    phone: str


@dataclass(frozen=True)
class Finish:
    credentials: TelegramCredentials


Action = (
    LoadCredentials  # noqa: WPS221  # 13-variant action sum type; one identifier per line is the readable form
    | RequestApiCredentials
    | RequestPhone
    | CheckAuthorization
    | RequestCode
    | RequestSmsCode
    | SignInWithCode
    | RequestPassword
    | SignInWithPassword
    | RestrictSession
    | PersistFullCredentials
    | PersistPhone
    | Finish
)


@dataclass(frozen=True)
class CredentialsLoaded:
    credentials: TelegramCredentials | None


@dataclass(frozen=True)
class ApiCredentialsProvided:
    api_id: int
    api_hash: str


@dataclass(frozen=True)
class PhoneProvided:
    phone: str


@dataclass(frozen=True)
class AuthorizationChecked:
    authorized: bool


@dataclass(frozen=True)
class CodeRequested:
    pass


@dataclass(frozen=True)
class SmsCodeProvided:
    code: str


@dataclass(frozen=True)
class SignInCompleted:
    password_required: bool


@dataclass(frozen=True)
class PasswordProvided:
    password: str


@dataclass(frozen=True)
class PasswordSignInCompleted:
    pass


@dataclass(frozen=True)
class SessionRestricted:
    pass


@dataclass(frozen=True)
class CredentialsPersisted:
    pass


Event = (
    CredentialsLoaded
    | ApiCredentialsProvided
    | PhoneProvided
    | AuthorizationChecked
    | CodeRequested
    | SmsCodeProvided
    | SignInCompleted
    | PasswordProvided
    | PasswordSignInCompleted
    | SessionRestricted
    | CredentialsPersisted
)


_PRE_LOGIN_EVENT_TYPES: tuple[type, ...] = (
    CredentialsLoaded,
    ApiCredentialsProvided,
    PhoneProvided,
    AuthorizationChecked,
)
_LOGIN_EVENT_TYPES: tuple[type, ...] = (
    CodeRequested,
    SmsCodeProvided,
    SignInCompleted,
    PasswordProvided,
    PasswordSignInCompleted,
)


def create_initial_state() -> AuthorizationState:
    return AuthorizationState()


def decide_next_action(state: AuthorizationState) -> Action:  # noqa: PLR0915  # FSM dispatcher: phase-ordered guard chain reads as a state-transition table; decomposing further would scatter it.
    pending = _decide_credential_resolution(state)
    if pending is not None:
        return pending
    credentials = state.credentials
    if credentials is None:
        raise AuthorizationFlowError("credentials must be resolved before authorization phase")
    pending = _decide_authorization(state, credentials)
    if pending is not None:
        return pending
    if not state.authorized:
        pending = _decide_login_dance(state, credentials)
        if pending is not None:
            return pending
    pending = _decide_persistence(state, credentials)
    if pending is not None:
        return pending
    if not state.session_restricted:
        return RestrictSession()
    return Finish(credentials)


def _decide_credential_resolution(state: AuthorizationState) -> Action | None:
    if not state.credentials_load_attempted:
        return LoadCredentials()
    if state.credentials is None:
        return RequestApiCredentials()
    if state.credentials.phone is None:
        return RequestPhone()
    return None


def _decide_authorization(state: AuthorizationState, credentials: TelegramCredentials) -> Action | None:
    if not state.authorization_checked:
        return CheckAuthorization(credentials)
    return None


def _decide_login_dance(state: AuthorizationState, credentials: TelegramCredentials) -> Action | None:
    phone = credentials.phone
    if phone is None:
        raise AuthorizationFlowError("login dance requires credentials.phone to be set")
    if not state.code_request_sent:
        return RequestCode(phone)
    if state.sms_code is None:
        return RequestSmsCode()
    if not state.sign_in_attempted:
        return SignInWithCode(phone, state.sms_code)
    if state.password_required:
        if state.password is None:
            return RequestPassword()
        if not state.password_sign_in_attempted:
            return SignInWithPassword(state.password)
    return None


def _decide_persistence(state: AuthorizationState, credentials: TelegramCredentials) -> Action | None:
    if state.persisted:
        return None
    if state.fresh_api_credentials:
        return PersistFullCredentials(credentials)
    if state.fresh_phone:
        phone = credentials.phone
        if phone is None:
            raise AuthorizationFlowError("fresh_phone is set but credentials.phone is None")
        return PersistPhone(phone)
    return None


def apply_event(state: AuthorizationState, event: Event) -> AuthorizationState:
    if isinstance(event, _PRE_LOGIN_EVENT_TYPES):
        return _apply_pre_login_event(state, event)
    if isinstance(event, _LOGIN_EVENT_TYPES):
        return _apply_login_event(state, event)
    return _apply_post_login_event(state, event)


def _apply_pre_login_event(state: AuthorizationState, event: Event) -> AuthorizationState:  # noqa: PLR0915  # FSM dispatcher: one match arm per pre-login event constructor.
    match event:
        case CredentialsLoaded(credentials):
            return replace(state, credentials_load_attempted=True, credentials=credentials)
        case ApiCredentialsProvided(api_id, api_hash):
            new_credentials = TelegramCredentials(api_id=api_id, api_hash=api_hash, phone=None)
            return replace(state, credentials=new_credentials, fresh_api_credentials=True)
        case PhoneProvided(phone):
            existing = state.credentials
            if existing is None:
                raise AuthorizationFlowError("PhoneProvided event requires existing credentials")
            new_credentials = replace(existing, phone=phone)
            return replace(state, credentials=new_credentials, fresh_phone=True)
        case AuthorizationChecked(authorized):
            return replace(state, authorization_checked=True, authorized=authorized)
    raise AuthorizationFlowError(f"unexpected pre-login event: {event!r}")


def _apply_login_event(state: AuthorizationState, event: Event) -> AuthorizationState:
    match event:
        case CodeRequested():
            return replace(state, code_request_sent=True)
        case SmsCodeProvided(code):
            return replace(state, sms_code=code)
        case SignInCompleted(password_required):
            return replace(state, sign_in_attempted=True, password_required=password_required)
        case PasswordProvided(password):
            return replace(state, password=password)
        case PasswordSignInCompleted():
            return replace(state, password_sign_in_attempted=True)
    raise AuthorizationFlowError(f"unexpected login event: {event!r}")


def _apply_post_login_event(state: AuthorizationState, event: Event) -> AuthorizationState:
    match event:
        case SessionRestricted():
            return replace(state, session_restricted=True)
        case CredentialsPersisted():
            return replace(state, persisted=True)
    raise AuthorizationFlowError(f"unexpected post-login event: {event!r}")
