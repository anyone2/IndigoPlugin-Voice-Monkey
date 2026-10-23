"""Voice Monkey client package.

Usage:
    from vm_client import make_client
    client = make_client('v2', access_token=..., secret_token=..., logger=...)
"""

from .base import VoiceMonkeyClientBase
from .v2 import VoiceMonkeyV2Client
from .v3 import VoiceMonkeyV3Client
from .errors import (
    VoiceMonkeyError,
    VMUnsupportedOperation,
    VMAuthError,
    VMDeviceNotFound,
    VMThrottled,
    VMQuotaExceeded,
    VMUpstreamError,
)

__all__ = [
    "make_client",
    "VoiceMonkeyClientBase",
    "VoiceMonkeyV2Client",
    "VoiceMonkeyV3Client",
    "VoiceMonkeyError",
    "VMUnsupportedOperation",
    "VMAuthError",
    "VMDeviceNotFound",
    "VMThrottled",
    "VMQuotaExceeded",
    "VMUpstreamError",
]


def make_client(api_version="v2", **kwargs):
    """Factory. api_version: 'v2' (default, legacy-compatible) or 'v3' (scaffold)."""
    if api_version in ("v2", "v2-legacy"):
        return VoiceMonkeyV2Client(**kwargs)
    if api_version == "v3":
        return VoiceMonkeyV3Client(**kwargs)
    raise ValueError(f"Unknown Voice Monkey api_version: {api_version!r}")
