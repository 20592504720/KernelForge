"""Best-effort diagnostic redaction, not a substitute for credential isolation."""
import re

_URL_USERINFO = re.compile(r"(?i)([a-z][a-z0-9+.-]*://)[^/\s?#@]+@")
_QUERY = re.compile(r"(?i)([?&](?:token|access_token|api[_-]?key|password|secret|signature|sig)=)[^&#\s]+")
_AUTH = re.compile(r"(?i)(\b(?:authorization|proxy-authorization)\s*:\s*(?:bearer|basic)\s+)[^\s,;]+")
_TOKENS = re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,}|AKIA[A-Z0-9]{16})\b")
_ASSIGN = re.compile(r"(?i)(\b(?:token|password|passwd|secret|api[_-]?key)\s*=\s*)[^\s,;&]+")


def redact_diagnostic(value: str) -> str:
    text = _URL_USERINFO.sub(r"\1[REDACTED]@", str(value))
    for pattern in (_QUERY, _AUTH, _ASSIGN):
        text = pattern.sub(r"\1[REDACTED]", text)
    return _TOKENS.sub("[REDACTED]", text)


def redact_tree(value):
    if isinstance(value, dict):
        return {key: redact_tree(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_tree(item) for item in value]
    if isinstance(value, str):
        return redact_diagnostic(value)
    return value
