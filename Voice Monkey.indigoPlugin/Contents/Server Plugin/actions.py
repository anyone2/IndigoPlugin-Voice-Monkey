"""Action wrappers — the plugin-callback bodies, ported off indigo.

Each function reproduces the corresponding legacy plugin.py callback's
behavior (line-cited) with the Indigo-specific machinery injected through
ActionServices. The future thin plugin.py callback will:
  1. do its ConfigUI/scripting validation (unchanged),
  2. resolve the device (monkey_id via config.DeviceSettings) — unchanged,
  3. call the wrapper here with plain values.

Ported this pass: text_to_speech (also serves SimpleSpeak — same callback,
empty-props path included), play_sound, play_audio_file, play_background_
audio_file, trigger_routine. NOT ported: Yes/No machinery (questions.py,
later pass), ARC/Announcements paths (bridges, later pass).

Intentionally preserved legacy log strings, including the 'Play a Audio File'
typo — existing log-watching habits/scripts must keep working.
"""

from constants import voices, sounds
from textutils import strip_newlines, ssml_escape


class ActionServices:
    """Indigo-side facilities injected into the wrappers.

    substitute(text) -> str   Indigo variable/device-state substitution
                              (plugin layer binds self.substitute)
    log_info(msg)             indigo.server.log(msg)
    log_error(msg)            self.logger.error(msg)
    wrap_log(text, entry)     legacy wrapLogging(text, entry)
                              (plugin layer binds textutils.format_wrapped_log
                               + indigo.server.log)
    Defaults are no-ops/identity so the wrappers are testable standalone.
    """

    def __init__(self, substitute=None, log_info=None,
                 log_error=None, wrap_log=None):
        self.substitute = substitute or (lambda text: text)
        self.log_info = log_info or (lambda msg: None)
        self.log_error = log_error or (lambda msg: None)
        self.wrap_log = wrap_log or (lambda text, entry: None)


EMPTY_TTS_PLACEHOLDER = ("No announcement text specified. Please update "
                         "the action to replace this message.")


def text_to_speech(services, client, monkey_id, dev_name, text,
                   change_voice=True, selected_voice=None, prefix_text=None):
    """Legacy plugin.py text_to_speech() L602-691.

    Also the SimpleSpeak callback path: SimpleSpeak has no ConfigUI, so a UI
    invocation arrives with empty text and takes the placeholder branch below
    (exact legacy behavior). `prefix_text` is the plugin_action.textToSpeak
    scripting quirk (L637-639). `change_voice` defaults True as in legacy
    props.get("ChangeVoice", True) (L673).
    """
    if prefix_text:
        text = f"{prefix_text} {text}"

    # L644-647: empty check happens BEFORE newline stripping
    if len(text) == 0 or text.isspace():
        services.log_error("Action has not been completely configured")
        text = EMPTY_TTS_PLACEHOLDER

    substituted = services.substitute(strip_newlines(text))

    if change_voice and selected_voice:
        voice = selected_voice
        # L676-677: unknown voices render as 'None' — legacy quirk, preserved
        voice_info = f"{voices.get(selected_voice)}"
    else:
        voice = None
        voice_info = "Alexa - Default"

    if client.announce(monkey_id, substituted, voice=voice):
        services.wrap_log(substituted,
                          f"{dev_name} : Text-to-Speech : {voice_info}")
        return True
    return False


def resolve_sound(value, scripted=False):
    """Legacy plugin.py play_sound() L1104-1114 sound resolution.

    UI path: `value` is a soundbank path (Actions.xml menu); display name via
    sounds dict with 'Tone 1' fallback. Scripted path: `value` is a display
    name; reverse-lookup the path, '' when unknown (legacy sends the malformed
    chime URL anyway — preserved, flagged in report §3 quirks).
    Returns (soundbank_path, display_name).
    """
    if scripted:
        display = value
        path = next((key for key, name in sounds.items() if name == value),
                    None)
        return (str(path) if path is not None else "", display)
    return value, sounds.get(value, "Tone 1")


def play_sound(services, client, monkey_id, dev_name, sound_value,
               scripted=False):
    """Legacy plugin.py play_sound() L1093-1153 (Voice Monkey API path only;
    the ARC override branch lives with arc_bridge in a later pass)."""
    path, display = resolve_sound(sound_value, scripted)
    if client.play_sound(monkey_id, path):
        services.log_info(f'{dev_name}: Play a Sound : "{display}"')
        return True
    return False


def play_audio_file(services, client, monkey_id, dev_name, url):
    """Legacy plugin.py play_audio_file_url() L968-1017."""
    substituted = services.substitute(strip_newlines(url))
    if client.play_audio(monkey_id, substituted):
        services.log_info(f'{dev_name}: Play a Audio File: "{substituted}"')
        return True
    return False


def play_background_audio_file(services, client, monkey_id, dev_name,
                               text, url):
    """Legacy plugin.py play_background_audio_file() L1020-1090."""
    substituted_url = services.substitute(strip_newlines(url))
    substituted_text = services.substitute(strip_newlines(text))
    if client.play_background_audio(monkey_id, substituted_text,
                                    substituted_url):
        services.wrap_log(substituted_url,
                          f"{dev_name}: Play Background Audio File")
        services.wrap_log(substituted_text, f"{dev_name} : Text-to-speech")
        return True
    return False


def trigger_routine(services, client, monkey_name):
    """Legacy plugin.py trigger_routine() L694-730. Logs the name as entered
    (pre-normalization), exactly like legacy."""
    if client.trigger_routine(monkey_name):
        services.log_info(f'Trigger a Routine : "{monkey_name}"')
        return True
    return False


# ---------------------------------------------------------------------------
# ARC-dependent thin wrappers (legacy plugin.py L1155-1398).
# `device_name` is the ALREADY-RESOLVED name — the plugin layer applies the
# alt-name logic (config.DeviceSettings.display_name) before calling these,
# exactly where legacy resolved it in each callback. `arc` is an
# arc_bridge.ArcBridge. Core Voice Monkey actions never require these.
# ---------------------------------------------------------------------------


def typed_request(services, arc, device_name, request):
    """Legacy typed_request() L1314-1342: sends a typed Alexa request via ARC.
    Silently does nothing when the request is empty (legacy `if the_request:`)."""
    if request:
        arc.ask_alexa(request, device_name)


def alexa_speak(services, arc, device_name, text,
                change_voice=True, selected_voice=None, prefix_text=None):
    """Legacy alexa_speak() L1234-1311 (hidden AlexaSpeak action / scripting).

    R7 FIX (post-bench cleanup): legacy checked only text.isspace(), so an
    EMPTY string slipped through and ARC was asked to speak ''. Now empty is
    rejected too, matching text_to_speech()'s check."""
    if prefix_text:
        text = f"{prefix_text} {text}"

    if len(text) == 0 or text.isspace():
        services.log_error("Action has not been completely configured")
        return False

    substituted = services.substitute(strip_newlines(text))
    ssml_text = ssml_escape(substituted)

    if change_voice:
        selected = selected_voice
        if selected:
            voice_info = f"{voices.get(selected)}"
        else:
            voice_info = "Alexa - Default"
    else:
        selected = None
        voice_info = "Alexa - Default"

    results = arc.alexa_speak(ssml_text, device_name, selected)
    if results:
        services.wrap_log(substituted,
                          f"{device_name} : Text-to-Speech : {voice_info}")
        return True
    return False


def alexa_routine(services, arc, device_name, routine_name):
    """Legacy alexa_routine() L1186-1231: run an Alexa routine by its exact
    Alexa-app name via ARC ('automation: <name>')."""
    arc.alexa_routine(routine_name, device_name)


def pass_device_arg(services, arc, device_name, arguments):
    """Legacy pass_device_arg() L1345-1373: raw ARC args with -d device."""
    if arguments:
        arc.pass_device_arg(arguments, device_name)


def pass_cmd_line_args(services, arc, arguments):
    """Legacy pass_cmd_line_args() L1376-1398: raw ARC args, no device."""
    if arguments:
        arc.pass_cmd_line_args(arguments)


def alexa_play_sound(services, arc, device_name, sound_path):
    """Legacy alexa_play_sound() L1158-1183: the ARC override for PlaySound
    (prefs forPlayingSounds). `sound_path` is the soundbank path from the UI
    menu; the bridge renders the audio SSML and log display name."""
    arc.alexa_play_sound(sound_path, device_name)
