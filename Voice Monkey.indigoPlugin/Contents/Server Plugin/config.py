"""Typed access to plugin preferences and per-device settings.

Rules (parity-critical):
- Every EXISTING pref/prop key keeps its legacy name and default. Nothing is
  renamed, removed, or re-typed on disk. Accessors read the same keys the
  legacy plugin.py reads (legacy defaults cited per accessor).
- New keys are ADDITIVE only and default to full legacy behavior:
    apiVersion   -> 'v2' (plugin pref; 'v3' opt-in later)
    v3ApiToken   -> ''   (plugin pref; v2 tokens are NOT reused for v3)
    v3DeviceId   -> ''   (device prop; v3 device IDs differ from monkey names)
- Deviation from legacy (defensive, flagged in task file): legacy did bare
  int(prefs.get(...)) in __init__ and crashed on malformed values; _int()
  falls back to the default instead. Values Indigo writes are well-formed,
  so behavior only differs on corrupt prefs.

Works with any mapping (indigo.Dict or plain dict). No indigo imports.
"""

from vm_client import VoiceMonkeyV2Client, VoiceMonkeyV3Client


def _int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class PluginSettings:
    """Typed view over the plugin prefs mapping (indigo.Dict or dict)."""

    def __init__(self, prefs):
        self._prefs = prefs

    # ---- Voice Monkey API (legacy keys: PluginConfig.xml) ---------------
    @property
    def access_token(self):                 # legacy default: unset -> ''
        return self._prefs.get("accessToken", "") or ""

    @property
    def secret_token(self):
        return self._prefs.get("secretToken", "") or ""

    # ---- additive keys (new; absent on existing installs) ---------------
    @property
    def api_version(self):
        """'v2' (default, legacy-compatible) or 'v3'. Additive key."""
        return self._prefs.get("apiVersion", "v2") or "v2"

    @property
    def v3_api_token(self):
        return self._prefs.get("v3ApiToken", "") or ""

    # ---- debug / logging (legacy plugin.py __init__ L33, L44-45) --------
    @property
    def show_debug_info(self):
        return bool(self._prefs.get("showDebugInfo", False))

    @property
    def max_text_length(self):
        return _int(self._prefs.get("maxTextLength", 150), 150)

    @property
    def max_combined_length(self):
        return _int(self._prefs.get("maxCombinedLength", 150), 150)

    # ---- Yes/No timing (legacy plugin.py __init__ L36-38) ---------------
    @property
    def sleep_time(self):
        return _int(self._prefs.get("sleepTime", 5), 5)

    @property
    def min_yes_no_delay(self):
        return _int(self._prefs.get("minYesNoDelay", 35), 35)

    @property
    def max_time_to_wait(self):
        return _int(self._prefs.get("maxTimeToWait", 30), 30)

    @property
    def adjust_timing(self):
        return bool(self._prefs.get("AdjustTiming", False))

    # ---- Announcements plugin subscription (legacy L57-61) --------------
    @property
    def enable_subscription(self):
        return bool(self._prefs.get("enableSubscription", False))

    @property
    def announcing_device(self):            # legacy default 0
        return self._prefs.get("announcingDevice", 0)

    @property
    def change_voice(self):
        return bool(self._prefs.get("ChangeVoice", False))

    @property
    def selected_voice(self):
        """Voice name or None (legacy stores False when unset)."""
        return self._prefs.get("selectedVoice", None) or None

    # ---- alexa-remote-control toggles (legacy PluginConfig.xml) ----------
    @property
    def use_alexa_remote_control(self):
        return bool(self._prefs.get("useAlexaRemoteControl", False))

    @property
    def arc_for_text_to_speech(self):       # legacy key forTextToSpeech
        return bool(self._prefs.get("forTextToSpeech", False))

    @property
    def arc_for_playing_sounds(self):       # legacy key forPlayingSounds
        return bool(self._prefs.get("forPlayingSounds", False))

    @property
    def alt_module_imported(self):
        """Mac Mini drift: hard-coded False in the running plugin (L48)."""
        return bool(self._prefs.get("AltModuleImported", False))

    # ---- hidden state ----------------------------------------------------
    @property
    def repeating_yes_no(self):
        """Raw pending-question store. SAME format as legacy 'RepeatingYesNo'
        pref — passed through untouched for upgrade compatibility."""
        return self._prefs.get("RepeatingYesNo", None)


class DeviceSettings:
    """Typed view over a VoiceMonkeyDevice's pluginProps mapping."""

    def __init__(self, props):
        self._props = props

    # ---- legacy props (Devices.xml) --------------------------------------
    @property
    def monkey_id(self):
        return self._props.get("monkey_id", "") or ""

    @property
    def yes_preset_id(self):
        return self._props.get("yes_preset_id", "") or ""

    @property
    def no_preset_id(self):
        return self._props.get("no_preset_id", "") or ""

    @property
    def use_alt_name(self):
        return bool(self._props.get("useAltName", False))

    @property
    def alt_device_name(self):
        return self._props.get("AltDeviceName", "") or ""

    # ---- additive prop ----------------------------------------------------
    @property
    def v3_device_id(self):
        """v3 device ID (additive). Empty on existing installs."""
        return self._props.get("v3DeviceId", "") or ""

    # ---- helpers -----------------------------------------------------------
    def api_device(self, api_version):
        """The device identifier to hand to the client for this API version."""
        if api_version == "v3":
            return self.v3_device_id
        return self.monkey_id

    def display_name(self, indigo_device_name):
        """Name used for ARC calls / logs: alt name when enabled, else the
        Indigo device name (legacy pattern, e.g. plugin.py L1175-1178)."""
        if self.use_alt_name and self.alt_device_name:
            return self.alt_device_name
        return indigo_device_name


def make_client_from_settings(settings, logger=None, transport=None):
    """Build the right vm_client for the configured api_version.

    Default ('v2') is byte-for-byte legacy behavior. 'v3' returns the scaffold
    client, which refuses all operations until v3 support is verified.
    """
    if settings.api_version == "v3":
        return VoiceMonkeyV3Client(token=settings.v3_api_token,
                                   logger=logger, transport=transport)
    return VoiceMonkeyV2Client(access_token=settings.access_token,
                               secret_token=settings.secret_token,
                               logger=logger, transport=transport)
