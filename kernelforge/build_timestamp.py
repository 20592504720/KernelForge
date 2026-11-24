"""Build timestamp policy for GitHub Actions and GKI/Vendor build adapters.

An omitted/blank value means the current UTC clock, captured once per build.
Custom input MUST contain a timezone and is canonicalized into UTC.
Never infer a timezone from the runner or the user's locale.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

_FORMAT = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(Z|[+-]\d{2}:\d{2})$"
)


class BuildTimestampError(ValueError):
    pass


def resolve_build_timestamp(requested: str | None = None,
                            *, now: datetime | None = None) -> dict:
    """Return a stable, timezone-explicit timestamp for an individual build.

    Parameters:
      "" or None: capture the current instant in UTC
      otherwise: strict ISO8601 seconds with Z or explicit +HH:MM/-HH:MM
    """
    if requested is None or requested == "":
        instant = datetime.now(timezone.utc) if now is None else now
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise BuildTimestampError("current clock must be timezone-aware")
        mode = "current_utc"
    else:
        if not isinstance(requested, str) or _FORMAT.fullmatch(requested) is None:
            raise BuildTimestampError(
                "custom build time must be YYYY-MM-DDTHH:MM:SSZ "
                "or YYYY-MM-DDTHH:MM:SS+08:00 with explicit timezone"
            )
        zone = requested[-6:] if requested[-1] != "Z" else "Z"
        if zone != "Z":
            hh = int(zone[1:3])
            mm = int(zone[4:6])
            if hh > 14 or mm > 59 or (hh == 14 and mm != 0):
                raise BuildTimestampError("custom timezone offset must be within 14 hours")
        try:
            instant = datetime.fromisoformat(requested.replace("Z", "+00:00"))
        except ValueError as exc:
            raise BuildTimestampError("invalid calendar date or time") from exc
        mode = "custom"
    utc = instant.astimezone(timezone.utc).replace(microsecond=0)
    if not 2000 <= utc.year <= 2100:
        raise BuildTimestampError("kernel build timestamp must be within 2000–2100 UTC")
    return {
        "mode": mode,
        "requested": requested if mode == "custom" else "",
        "utc_iso8601": utc.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "source_date_epoch": int(utc.timestamp()),
        "kbuild_build_timestamp": utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "timezone": "UTC",
    }


def kernel_build_environment(stamp: dict) -> dict[str, str]:
    """Output for a controlled subprocess environment, not global os.environ."""
    if (type(stamp) is not dict
            or type(stamp.get("source_date_epoch")) is not int
            or not isinstance(stamp.get("kbuild_build_timestamp"), str)):
        raise BuildTimestampError("invalid resolved build timestamp")
    return {
        "KBUILD_BUILD_TIMESTAMP": stamp["kbuild_build_timestamp"],
        "SOURCE_DATE_EPOCH": str(stamp["source_date_epoch"]),
    }
