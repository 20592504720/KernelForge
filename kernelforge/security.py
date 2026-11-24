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


# Do not publish raw subprocess output. A bounded line reader avoids loading
# pathological individual lines into memory; overlong lines are discarded whole.
_LOG_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
LOG_LINE_LIMIT = 64 * 1024
LOG_PUBLISH_LIMIT = 128 * 1024**2


def publish_redacted_log(source, destination, *, line_limit=LOG_LINE_LIMIT,
                         byte_limit=LOG_PUBLISH_LIMIT):
    if type(line_limit) is not int or line_limit < 1 or type(byte_limit) is not int or byte_limit < 1:
        raise ValueError("invalid diagnostic log budget")
    source.seek(0)
    written = 0
    truncated = False
    while True:
        raw = source.readline(line_limit + 1)
        if not raw:
            break
        if len(raw) > line_limit:
            while not raw.endswith(b"\n"):
                raw = source.readline(line_limit + 1)
                if not raw:
                    break
            text = "[REDACTED: overlong diagnostic line]\n"
        else:
            line = raw.decode("utf-8", errors="replace")
            line = _ANSI.sub("", line)
            line = _LOG_CONTROL.sub("", line)
            text = redact_diagnostic(line)
        length = len(text.encode("utf-8"))
        if written + length > byte_limit:
            truncated = True
            break
        destination.write(text)
        written += length
    if truncated:
        destination.write("\n[diagnostic log truncated at configured byte limit]\n")
    return {"published_bytes": written, "truncated": truncated,
            "policy": "BEST_EFFORT_REDACTED_NOT_RAW"}
