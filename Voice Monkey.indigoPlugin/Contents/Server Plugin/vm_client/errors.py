"""Typed exceptions for the Voice Monkey client layer.

The v2 client preserves legacy behavior (returns bool, logs sanitized errors) and
does not raise these for transport failures. They exist primarily for the v3 client
(mapped from documented v3 error JSON) and for explicit unsupported operations.
"""


class VoiceMonkeyError(Exception):
    """Base class for Voice Monkey client errors."""


class VMUnsupportedOperation(VoiceMonkeyError):
    """Operation not supported by this client / API version (yet)."""


class VMAuthError(VoiceMonkeyError):
    """401 UNAUTHORIZED / INVALID_TOKEN."""


class VMDeviceNotFound(VoiceMonkeyError):
    """404 DEVICE_NOT_FOUND (or 400 MISSING_DEVICE)."""


class VMThrottled(VoiceMonkeyError):
    """429 THROTTLED — back off until lockoutUntil."""


class VMQuotaExceeded(VoiceMonkeyError):
    """429 MONTHLY_QUOTA_EXCEEDED."""


class VMUpstreamError(VoiceMonkeyError):
    """500 ALEXA_TRIGGER_FAILED or other upstream failure."""
