"""Announcements/Salutations plugin bridge — OPTIONAL, cleanly severable.

Ports legacy plugin.py announcement_speak_action() (L2633-2738). All Indigo and
Announcements-plugin touchpoints are injected via AnnouncementsServices; no
indigo imports; the core Voice Monkey client has no dependency on this module.

The variable-subscription flow (spoken_announcement_raw) and the dynamic
ConfigUI list generators stay in the plugin layer (they are indigo.devices /
startup concerns) — this module owns only the speak-an-announcement behavior.

Preserved legacy behaviors:
- ANN-A: announcement names match after replacing '_' with ' ' (Indigo state
  ids use underscores; Announcement names use spaces).
- ANN-B: '[[...]]' embedded speech commands are rejected with the legacy error
  text; '<<...>>' triggers a refresh + 0.5 s sleep + device-state read.
- ANN-C: any device whose model is not "Announcements Device" is treated as a
  Salutations device and spoken from its state value directly.
- ANN-D: legacy error/warn strings preserved verbatim, including the trailing
  space in "The selected Announcements is not enabled. ".

Announcements plugin id: com.fogbert.indigoplugin.announcements
"""

import json

ANNOUNCEMENTS_PLUGIN_ID = "com.fogbert.indigoplugin.announcements"


class AnnouncementsServices:
    """Injected facilities.

    is_plugin_running()            -> bool (Announcements plugin enabled)
    get_device(dev_id)             -> device object or None; devices expose
                                      .model, .enabled, .states (mapping)
    export_announcements()         -> JSON string from the Announcements
                                      plugin's exportAnnouncements action
    refresh_announcement(name, source_id)
                                   -> the plugin's refreshAnnouncementData
    sleep(seconds)                 -> plugin-safe sleep (legacy self.sleep)
    speak(text, change_voice, selected_voice)
                                   -> routes to the TTS wrapper for the
                                      target Voice Monkey device
    log_error/log_warn/log_debug   -> logger levels
    """

    def __init__(self, is_plugin_running, get_device, export_announcements,
                 refresh_announcement, sleep, speak,
                 log_error=None, log_warn=None, log_debug=None):
        self.is_plugin_running = is_plugin_running
        self.get_device = get_device
        self.export_announcements = export_announcements
        self.refresh_announcement = refresh_announcement
        self.sleep = sleep
        self.speak = speak
        self.log_error = log_error or (lambda msg: None)
        self.log_warn = log_warn or (lambda msg: None)
        self.log_debug = log_debug or (lambda msg: None)


def announcement_speak_action(services, props):
    """Legacy plugin.py announcement_speak_action() L2633-2738."""
    services.log_debug("announcement_speak_action")

    if not services.is_plugin_running():
        services.log_error(
            "The Announcements Plugin is not enabled. "
            "The 'Speak Announcements' Device Action requires it.")
        return False

    source_id = int(props["theAnnouncement"])
    announcement_name = props["announcementToSpeak"]

    selected_voice = props.get("selectedAnnouncementVoice", False)
    change_voice = props.get("ChangeAnnouncementVoice", True)

    source_dev = services.get_device(source_id)

    if source_dev is None:
        services.log_error(
            "Announcements device not found. Please edit the "
            "Action Group and select another device.")
        return False

    elif not source_dev.enabled:
        # quirk ANN-D: trailing space preserved
        services.log_warn("The selected Announcements is not enabled. ")
        return False

    elif source_dev.model == "Announcements Device":

        exported_announcements = json.loads(services.export_announcements())
        announcements = exported_announcements[str(source_id)]

        # quirk ANN-A: underscores -> spaces before matching
        matching_name = announcement_name.replace("_", " ")
        matching_items = [v for k, v in announcements.items()
                          if v["Name"] == matching_name]
        announcement_message = (matching_items[0]["Announcement"]
                                if matching_items else None)

        if announcement_message is not None:

            if ("[[" in announcement_message
                    and "]]" in announcement_message):
                services.log_error(
                    "This plugin cannot interpret speech commands "
                    "in the selected announcement. Please update "
                    "the announcement with Speech Synthesis "
                    "Markup Language (SSML) commands.")
                return False

            elif ("<<" in announcement_message
                    and ">>" in announcement_message):
                # refresh, wait for the device state to update, then read it
                services.refresh_announcement(announcement_name, source_id)
                services.sleep(0.5)
                text_to_speak = source_dev.states[announcement_name]

            else:  # no modifiers used
                text_to_speak = announcement_message

            services.speak(text_to_speak, change_voice, selected_voice)

        else:  # announcement not found
            services.log_warn("The configured Announcement was not found")

    else:  # quirk ANN-C: "Salutations Device" (any non-Announcements model)
        text_to_speak = source_dev.states[announcement_name]
        services.speak(text_to_speak, change_voice, selected_voice)
