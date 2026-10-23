"""VoiceMonkeyV3Client — SCAFFOLD ONLY. Explicitly unsupported until verified.

Documented v3 surface (voicemonkey.io docs, fetched 2026-07-02):
- Host: https://api-v3.voicemonkey.io
- POST /announce   body: token, device (v3 device ID), speech, voice, language,
                   chime, audio, background_audio, image, video, ...
- POST /trigger    fires routine triggers
- v2 and v3 tokens are NOT interchangeable; v3 device IDs differ from v2 monkey names.

Yes/No questions: no direct /announce API equivalent was found for the current
prompt-yes-preset / prompt-no-preset mechanism. Yes/No appears likely to be
Flow/Question-node based in v3 and should be investigated once v3 access is
available. Until then ask_yes_no() (and everything else here) raises
VMUnsupportedOperation; the plugin keeps using the v2 client.

Nick's account is a v2 account (v3 is invitation-only for pre-2026-04-27 signups),
so nothing in this class can be verified against a live account yet. Do not
implement further until v3 access exists and behavior can be tested.
"""

from .base import VoiceMonkeyClientBase
from .errors import VMUnsupportedOperation

V3_HOST = "https://api-v3.voicemonkey.io"

_NOT_READY = ("Voice Monkey v3 support is scaffolded but not implemented — "
              "v3 account access is pending and behavior is unverified. "
              "Use api_version 'v2'.")

_YES_NO_NOTE = ("Yes/No questions: no direct v3 /announce equivalent found for the "
                "v2 prompt-yes-preset/prompt-no-preset mechanism; appears likely to "
                "be Flow/Question-node based. Investigate once v3 access is "
                "available. Use the v2 client for Yes/No until verified.")


class VoiceMonkeyV3Client(VoiceMonkeyClientBase):
    api_version = "v3"

    def __init__(self, token=None, base_url=V3_HOST, timeout=5,
                 transport=None, logger=None):
        super().__init__(logger=logger)
        self.token = token or ""
        self.base_url = base_url
        self.timeout = timeout
        self._transport = transport

    def announce(self, device, text, voice=None):
        raise VMUnsupportedOperation(_NOT_READY)

    def trigger_routine(self, trigger_id):
        raise VMUnsupportedOperation(_NOT_READY)

    def ask_yes_no(self, device, question, yes_preset, no_preset):
        raise VMUnsupportedOperation(f"{_NOT_READY} {_YES_NO_NOTE}")

    def play_sound(self, device, soundbank_path):
        raise VMUnsupportedOperation(_NOT_READY)

    def play_audio(self, device, url):
        raise VMUnsupportedOperation(_NOT_READY)

    def play_background_audio(self, device, text, url):
        raise VMUnsupportedOperation(_NOT_READY)

    def sanitize(self, text):
        if self.token:
            text = text.replace(self.token, "V3_TOKEN")
        return text
