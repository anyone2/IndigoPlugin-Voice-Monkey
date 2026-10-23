"""VoiceMonkeyClientBase — semantic API hiding v2/v3 differences from the plugin.

Responsibility contract (parity-critical; see first-pass report §5):

  The PLUGIN layer (Indigo-side) is responsible for:
    - stripping newline characters (textutils.strip_newlines)
    - Indigo variable/device-state substitution (self.substitute())
    - empty-text placeholder messages and ConfigUI validation
    - success/outcome logging in the established log format (wrapLogging)

  The CLIENT layer (this package) is responsible for:
    - SSML '&' escaping where the legacy plugin applied it
    - URL/parameter encoding exactly as the legacy plugin did
    - monkey-name / device-id resolution formatting
    - transport, timeouts, and SANITIZED debug/error logging
      (tokens must never appear in any log record)

`device` in the semantic methods is the v2 monkey name (v2 client) or the v3
device ID (v3 client). The plugin layer chooses which value to pass based on the
configured api_version.
"""

import logging


class VoiceMonkeyClientBase:
    api_version = "abstract"

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger("Plugin.vm_client")

    # ---- semantic API -------------------------------------------------
    def announce(self, device, text, voice=None):
        """Text-to-speech on a device. `text` is post-substitution, newline-free."""
        raise NotImplementedError

    def trigger_routine(self, trigger_id):
        """Fire a routine trigger by name/ID."""
        raise NotImplementedError

    def ask_yes_no(self, device, question, yes_preset, no_preset):
        """Ask a Yes/No question with response presets (v2 mechanism)."""
        raise NotImplementedError

    def play_sound(self, device, soundbank_path):
        """Play a built-in Alexa soundbank sound. `soundbank_path` is the path
        segment as stored in constants.sounds keys (e.g. '/home/amzn_sfx_doorbell_01')."""
        raise NotImplementedError

    def play_audio(self, device, url):
        """Play an audio file by public https URL."""
        raise NotImplementedError

    def play_background_audio(self, device, text, url):
        """TTS with background audio playing underneath."""
        raise NotImplementedError

    # ---- shared helpers ------------------------------------------------
    def sanitize(self, text):
        """Return `text` with any secret material replaced by placeholders."""
        raise NotImplementedError
