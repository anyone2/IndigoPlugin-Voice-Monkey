"""VoiceMonkeyV2Client — legacy-compatible Voice Monkey client.

Compatibility baseline (this pass): the CURRENT running plugin's API usage —
GET https://api.voicemonkey.io/trigger?access_token=..&secret_token=..&monkey=..&...

Every build_*_url() method reproduces the legacy plugin.py construction
byte-for-byte. Golden tests in tests/test_golden_requests.py compare against
tests/legacy_reference.py, which replicates the original code verbatim.

Intentionally preserved legacy oddities (do not "fix" without a sign-off):
- tokens are NOT URL-encoded (legacy f-string interpolation)
- monkey names are normalized but NOT URL-encoded
- `voice` value is appended raw, not URL-encoded
- speech text uses quote() (spaces -> %20); media URLs use quote_plus() (spaces -> +)
- play_sound/play_audio send a literal '&announcement=%20' placeholder
- only '&' is SSML-escaped in speech text (not a full XML escape)
- on transport failure: log sanitized error, return False (no raise)

The host/endpoint is configurable (base_url) so a later pass can move to the
documented v2 host without touching call sites; the default is today's exact URL.
"""

from urllib.parse import quote, quote_plus

from .base import VoiceMonkeyClientBase

try:
    from textutils import ssml_escape, normalize_monkey_name
except ImportError:  # package-relative fallback if textutils sits beside vm_client
    from ..textutils import ssml_escape, normalize_monkey_name  # type: ignore


DEFAULT_BASE_URL = "https://api.voicemonkey.io/trigger"
DEFAULT_TIMEOUT = 5  # seconds — matches legacy plugin.py make_request()


def _default_transport(url, timeout):
    """Default HTTP transport. Imported lazily so tests never need `requests`."""
    import requests

    return requests.get(url, timeout=timeout)


class VoiceMonkeyV2Client(VoiceMonkeyClientBase):
    api_version = "v2-legacy"

    def __init__(self, access_token, secret_token,
                 base_url=DEFAULT_BASE_URL, timeout=DEFAULT_TIMEOUT,
                 transport=None, logger=None):
        super().__init__(logger=logger)
        self.access_token = access_token or ""
        self.secret_token = secret_token or ""
        self.base_url = base_url
        self.timeout = timeout
        self._transport = transport or _default_transport

    # ---- URL builders (pure functions of input; golden-tested) --------

    def _url(self, query):
        # legacy plugin.py make_request() L2816-2819
        return (f"{self.base_url}?"
                f"access_token={self.access_token}"
                f"&secret_token={self.secret_token}"
                f"{query}")

    def build_announce_url(self, device, text, voice=None):
        # legacy plugin.py text_to_speech() L661-681
        query = (f"&monkey={normalize_monkey_name(device)}"
                 f"&announcement={quote(ssml_escape(text))}")
        if voice:
            query += f"&voice={voice}"
        return self._url(query)

    def build_trigger_routine_url(self, trigger_id):
        # legacy plugin.py trigger_routine() L715-721
        return self._url(f"&monkey={normalize_monkey_name(trigger_id)}")

    def build_ask_yes_no_url(self, device, question, yes_preset, no_preset):
        # legacy plugin.py yes_no_question() L852-873
        return self._url(
            f"&monkey={normalize_monkey_name(device)}"
            f"&announcement={quote(ssml_escape(question))}"
            f"&prompt-yes-preset={yes_preset}"
            f"&prompt-no-preset={no_preset}")

    def build_play_sound_url(self, device, soundbank_path):
        # legacy plugin.py play_sound() L1133-1145
        chime = quote_plus(f"soundbank://soundlibrary{soundbank_path}")
        return self._url(
            f"&monkey={normalize_monkey_name(device)}"
            f"&announcement=%20"
            f"&chime={chime}")

    def build_play_audio_url(self, device, url):
        # legacy plugin.py play_audio_file_url() L1000-1009
        return self._url(
            f"&monkey={normalize_monkey_name(device)}"
            f"&announcement=%20"
            f"&audio={quote_plus(url)}")

    def build_play_background_audio_url(self, device, text, url):
        # legacy plugin.py play_background_audio_file() L1064-1079
        return self._url(
            f"&monkey={normalize_monkey_name(device)}"
            f"&announcement={quote(ssml_escape(text))}"
            f"&bkg-audio={quote_plus(url)}")

    # ---- semantic API --------------------------------------------------

    def announce(self, device, text, voice=None):
        return self._send(self.build_announce_url(device, text, voice))

    def trigger_routine(self, trigger_id):
        return self._send(self.build_trigger_routine_url(trigger_id))

    def ask_yes_no(self, device, question, yes_preset, no_preset):
        return self._send(
            self.build_ask_yes_no_url(device, question, yes_preset, no_preset))

    def play_sound(self, device, soundbank_path):
        return self._send(self.build_play_sound_url(device, soundbank_path))

    def play_audio(self, device, url):
        return self._send(self.build_play_audio_url(device, url))

    def play_background_audio(self, device, text, url):
        return self._send(
            self.build_play_background_audio_url(device, text, url))

    # ---- transport and safety -------------------------------------------

    def sanitize(self, text):
        """Replace token values with placeholders. Null-safe (legacy version
        raised TypeError when a token was unset — behavior-preserving fix)."""
        for value, placeholder in ((self.access_token, "ACCESS_TOKEN"),
                                   (self.secret_token, "SECRET_TOKEN")):
            if value:
                text = text.replace(value, placeholder)
        return text

    def _send(self, url):
        """GET the built URL. Returns True on 2xx, False otherwise.
        Mirrors legacy make_request(): sanitized debug URL, raise_for_status,
        sanitized error logging, boolean result, no exception propagation."""
        self.logger.debug(self.sanitize(url))
        try:
            response = self._transport(url, self.timeout)
            self.logger.debug(f"response: {response}")
            response.raise_for_status()
            self.logger.debug(
                "Your request queued successfully. "
                "This doesn't guarantee the Monkey will trigger.")
            return True
        except Exception as e:
            self.logger.error(self.sanitize(str(e)))
            return False
