import hashlib
import hmac
import logging
import time
from typing import Any, Optional
from urllib.parse import quote

import jwt
from open_webui.env import (
    FORWARD_USER_INFO_HEADER_JWT,
    FORWARD_USER_INFO_HEADER_JWT_EXPIRES_SECONDS,
    FORWARD_USER_INFO_HEADER_JWT_SECRET,
    FORWARD_USER_INFO_HEADER_USER_EMAIL,
    FORWARD_USER_INFO_HEADER_USER_ID,
    FORWARD_USER_INFO_HEADER_USER_NAME,
    FORWARD_USER_INFO_HEADER_USER_ROLE,
    FORWARD_USER_INFO_PSEUDONYM_LENGTH,
    FORWARD_USER_INFO_PSEUDONYM_SECRET,
)
from open_webui.models.groups import Groups

log = logging.getLogger(__name__)

USER_GROUPS_PLACEHOLDERS = ('{{USER_GROUPS}}', '{{USER_GROUP_IDS}}')


def normalize_bearer_token(token: Any) -> str:
    return token.strip() if isinstance(token, str) else token or ''


def bearer_auth_header(token: Any) -> dict[str, str]:
    token = normalize_bearer_token(token)
    return {'Authorization': f'Bearer {token}'} if token else {}


def get_json_bearer_headers(token: Any = '') -> dict[str, str]:
    return {'Content-Type': 'application/json', **bearer_auth_header(token)}


def _mint_forward_user_jwt(user: Any) -> str:
    now = int(time.time())
    payload = {
        'sub': str(user.id),
        'email': str(user.email),
        'name': str(user.name),
        'role': str(user.role),
        'iss': 'open-webui',
        'iat': now,
        'exp': now + FORWARD_USER_INFO_HEADER_JWT_EXPIRES_SECONDS,
    }
    return jwt.encode(payload, FORWARD_USER_INFO_HEADER_JWT_SECRET, algorithm='HS256')


def include_user_info_headers(headers: dict, user: Optional[Any] = None) -> dict:
    """
    Forward user identity to external backends: signed JWT in
    FORWARD_USER_INFO_HEADER_JWT if FORWARD_USER_INFO_HEADER_JWT_SECRET is set;
    otherwise the legacy X-OpenWebUI-User-* headers.
    """
    if user is None:
        return headers

    if FORWARD_USER_INFO_HEADER_JWT_SECRET:
        try:
            token = _mint_forward_user_jwt(user)
            return {**headers, FORWARD_USER_INFO_HEADER_JWT: token}
        except Exception:
            log.exception(
                'Failed to mint %s; falling back to plain user-info headers.',
                FORWARD_USER_INFO_HEADER_JWT,
            )

    return {
        **headers,
        FORWARD_USER_INFO_HEADER_USER_NAME: quote(user.name.strip(), safe=' '),
        FORWARD_USER_INFO_HEADER_USER_ID: user.id,
        FORWARD_USER_INFO_HEADER_USER_EMAIL: user.email.strip(),
        FORWARD_USER_INFO_HEADER_USER_ROLE: user.role,
    }


def custom_headers_require_user_groups(custom_headers: Optional[dict]) -> bool:
    if not custom_headers or not isinstance(custom_headers, dict):
        return False
    return any(
        placeholder in str(value) for value in custom_headers.values() for placeholder in USER_GROUPS_PLACEHOLDERS
    )


async def get_user_groups_for_custom_headers(
    custom_headers: Optional[dict], user: Optional[Any] = None
) -> Optional[list]:
    """Fetch the user's groups only when a header value actually references a groups placeholder."""
    if user is None or not custom_headers_require_user_groups(custom_headers):
        return None

    try:
        return await Groups.get_groups_by_member_id(user.id)
    except Exception:
        log.exception('Failed to resolve user groups for custom headers')
        return None


async def get_custom_headers(custom_headers: dict, user=None, metadata: dict = None, request=None) -> dict:
    user_groups = await get_user_groups_for_custom_headers(custom_headers, user)
    return parse_custom_headers(custom_headers, user, metadata, request=request, user_groups=user_groups)


def pseudonymize(value: str) -> str:
    """
    Stable HMAC-SHA256 pseudonym for *value*, for gateways that need to attribute
    usage per user without receiving a directly identifying value.

    Returns an empty string when no salt is configured, so a missing
    FORWARD_USER_INFO_PSEUDONYM_SECRET drops the placeholder rather than silently
    forwarding the raw identifier.
    """
    if not value or not FORWARD_USER_INFO_PSEUDONYM_SECRET:
        return ''

    digest = hmac.new(
        FORWARD_USER_INFO_PSEUDONYM_SECRET.encode('utf-8'),
        value.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()
    return digest[:FORWARD_USER_INFO_PSEUDONYM_LENGTH]


def build_template_vars(
    user=None, metadata: dict = None, request=None, user_groups: list | None = None
) -> dict[str, str]:
    """Placeholder values shared by the per-connection `headers` and `body` templates."""
    metadata = metadata or {}

    # UA from the live request; fall back to metadata for detached RAG/tool calls.
    user_agent = ''
    if request is not None:
        try:
            user_agent = request.headers.get('user-agent', '') or ''
        except Exception:
            user_agent = ''
    if not user_agent:
        user_agent = metadata.get('user_agent', '') or ''

    # Extract user_message info for tree mapping
    user_message = metadata.get('user_message') or {}
    user_message_id = metadata.get('user_message_id', '') or (user_message.get('id', '') if user_message else '')
    user_message_parent_id = user_message.get('parentId', '') if user_message else ''

    user_id = (user.id if user else '') or ''
    user_email = (user.email.strip() if user else '') or ''

    return {
        '{{CHAT_ID}}': metadata.get('chat_id', '') or '',
        '{{MESSAGE_ID}}': metadata.get('message_id', '') or '',
        '{{USER_MESSAGE_ID}}': user_message_id or '',
        '{{USER_MESSAGE_PARENT_ID}}': user_message_parent_id or '',
        '{{FILE_ID}}': metadata.get('file_id', '') or '',
        '{{FILE_NAME}}': metadata.get('file_name', '') or '',
        '{{FILE_CONTENT_TYPE}}': metadata.get('file_content_type', '') or '',
        '{{TASK}}': metadata.get('task', '') or '',
        '{{USER_ID}}': user_id,
        '{{USER_NAME}}': (user.name.strip() if user else '') or '',
        '{{USER_EMAIL}}': user_email,
        '{{USER_ROLE}}': (user.role if user else '') or '',
        '{{USER_GROUPS}}': ','.join(group.name.strip() for group in user_groups) if user_groups else '',
        '{{USER_GROUP_IDS}}': ','.join(group.id for group in user_groups) if user_groups else '',
        '{{USER_AGENT}}': user_agent,
        '{{USER_ID_HASH}}': pseudonymize(user_id),
        '{{USER_EMAIL_HASH}}': pseudonymize(user_email),
    }


def parse_custom_headers(
    custom_headers: dict, user=None, metadata: dict = None, request=None, user_groups: Optional[list] = None
) -> dict:
    if not custom_headers or not isinstance(custom_headers, dict):
        return {}

    template_vars = build_template_vars(user, metadata, request=request, user_groups=user_groups)

    parsed_headers = {}
    for key, value in custom_headers.items():
        if not isinstance(value, str):
            value = str(value)
        for token, val in template_vars.items():
            value = value.replace(token, val)
        parsed_headers[key] = value

    return parsed_headers


def _substitute(value: Any, template_vars: dict[str, str]) -> Any:
    """Apply {{PLACEHOLDER}} substitution to every string nested inside *value*."""
    if isinstance(value, str):
        for token, val in template_vars.items():
            value = value.replace(token, val)
        return value
    if isinstance(value, dict):
        return {key: _substitute(item, template_vars) for key, item in value.items()}
    if isinstance(value, list):
        return [_substitute(item, template_vars) for item in value]
    return value


def _drop_empty(value: Any) -> Any:
    """
    Drop keys whose templated value resolved to nothing, so an unavailable
    placeholder (no chat_id on a task request, say) leaves the key out entirely
    instead of sending an empty string upstream.
    """
    if isinstance(value, dict):
        pruned = {key: _drop_empty(item) for key, item in value.items()}
        return {key: item for key, item in pruned.items() if item not in ('', {}, [])}
    if isinstance(value, list):
        return [_drop_empty(item) for item in value]
    return value


# Content-bearing keys a `body` template must never overwrite; a deep merge onto these
# would corrupt the conversation rather than annotate the request.
RESERVED_BODY_KEYS = frozenset({'messages', 'input', 'model', 'stream'})


def parse_custom_body(
    custom_body: dict, user=None, metadata: dict = None, request=None, user_groups: list | None = None
) -> dict:
    """
    Resolve a per-connection `body` template into the fields to merge into an
    outgoing request payload. Same placeholders as `headers`, but nested values are
    preserved, which is what gateways expecting a structured field want (for example
    Databricks `usage_context`).
    """
    if not custom_body or not isinstance(custom_body, dict):
        return {}

    reserved = RESERVED_BODY_KEYS.intersection(custom_body)
    if reserved:
        log.warning('Ignoring reserved key(s) %s in connection body template', ', '.join(sorted(reserved)))
        custom_body = {key: value for key, value in custom_body.items() if key not in RESERVED_BODY_KEYS}

    template_vars = build_template_vars(user, metadata, request=request, user_groups=user_groups)
    return _drop_empty(_substitute(custom_body, template_vars))


async def get_custom_body(custom_body: dict, user=None, metadata: dict = None, request=None) -> dict:
    user_groups = await get_user_groups_for_custom_headers(custom_body, user)
    return parse_custom_body(custom_body, user, metadata, request=request, user_groups=user_groups)
