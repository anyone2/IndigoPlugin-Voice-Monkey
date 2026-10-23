#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Voice Monkey plugin — rewritten Indigo layer.
#
# This file is deliberately THIN: every callback delegates to the tested
# modules (vm_client, actions, questions, arc_bridge, announcements_bridge,
# config, textutils, constants). Action IDs, callback names, config keys,
# device props/states, log formats, and voice_monkey.py scripting signatures
# are unchanged from the legacy plugin. Legacy quirks are preserved and
# documented in the modules (report §3; Q-A..G; ARC-A..D; ANN-A..D).

import json
import re
from datetime import datetime

import indigo

import actions
import announcements_bridge
import arc_bridge
from config import PluginSettings, make_client_from_settings
from constants import voices, sounds
from questions import QuestionManager, QuestionServices
from textutils import format_wrapped_log


###########################
class actionDict():
    """Internal action stand-in used by scripted/synthesized calls (legacy)."""

    def __init__(self, description, pluginTypeId, props):
        self.description = description
        self.pluginTypeId = pluginTypeId
        self.props = props


class _FreshClient:
    """Delegates every client call to a freshly built client so pref/token
    changes apply immediately, matching legacy make_request() reading prefs
    on every call."""

    def __init__(self, plugin):
        self._plugin = plugin

    def __getattr__(self, name):
        return getattr(self._plugin._client(), name)


################################
class Plugin(indigo.PluginBase):

    def __init__(self, plugin_id, plugin_display_name, plugin_version, plugin_prefs):  # noqa
        super().__init__(plugin_id, plugin_display_name, plugin_version, plugin_prefs)  # noqa

        self.settings = PluginSettings(plugin_prefs)

        # retain the configurable logging state
        self.debug = self.settings.show_debug_info

        # configurable settings for Yes/No Question prompting
        self.sleep_time = self.settings.sleep_time
        self.min_delay = self.settings.min_yes_no_delay
        self.max_wait = self.settings.max_time_to_wait

        # configurable settings for output to the log
        self.max_text_length = self.settings.max_text_length
        self.max_combined_length = self.settings.max_combined_length

        # NOTE (R23): self.plugin_prefs and self.pluginPrefs are Indigo
        # PluginBase aliases for the SAME prefs mapping. This file uses both
        # spellings (legacy parity) — do not assume they can diverge, and do
        # not "unify" them without verifying alias identity on the target
        # Indigo version.

        # Announcements plugin integration
        self.subscription_variable = "spoken_announcement_raw"
        self.announcements_pid = "com.fogbert.indigoplugin.announcements"
        self.announcing_device = self.plugin_prefs.get("announcingDevice", 0)
        self.change_voice = self.plugin_prefs.get("ChangeVoice", False)
        self.selected_voice = self.plugin_prefs.get("selectedVoice", False)
        self.subscription_enabled = False

        # ---- module wiring -------------------------------------------------
        self.vm_services = actions.ActionServices(
            substitute=self.substitute,
            log_info=indigo.server.log,
            log_error=self.logger.error,
            wrap_log=self.wrapLogging)

        self.arc = arc_bridge.ArcBridge(
            log_typed=indigo.server.log,
            log_info=self.logger.info,
            log_warn=self.logger.warn,
            log_error=self.logger.error,
            log_debug=self.logger.debug,
            emit=print)

        # ARC availability detection RESTORED to upstream behavior (bench
        # issue 2026-07-02: the Mac Mini drift hard-coded this to False, which
        # made configuring ARC-dependent actions fail with "Additional
        # configuration is required. This is not a capability of the Voice
        # Monkey API." even with the script installed).
        plugin_prefs["AltModuleImported"] = self.arc.does_script_exist()

        q_services = QuestionServices(
            get_device=lambda dev_id: indigo.devices.get(int(dev_id)),
            execute_action_group=indigo.actionGroup.execute,
            update_states=lambda dev, mapping: dev.updateStatesOnServer(
                [{"key": k, "value": v} for k, v in mapping.items()]),
            confirm_test=self.confirm_test,
            substitute=self.substitute,
            wrap_log=self.wrapLogging,
            log_info=self.logger.info,
            log_warn=self.logger.warn,
            log_error=self.logger.error,
            log_critical=self.logger.critical,
            log_debug=self.logger.debug,
            now=lambda: datetime.now().timestamp())
        self.questions = QuestionManager(q_services, _FreshClient(self),
                                         max_wait=self.max_wait)
        self.questions.load_state(
            plugin_prefs.get("RepeatingYesNo", indigo.Dict()))

    # -------------------------------------------------------------------
    def _client(self):
        """Fresh client from current prefs (v2 default; v3 opt-in refuses)."""
        return make_client_from_settings(self.settings, logger=self.logger)

    ########################################
    def startup(self):
        self.logger.debug("startup called")

        # show pending questions on startup
        self.show_pending_questions()

        # check if the Alexa Plugin is running
        alexa_result = self.isPluginRunning("alexa")
        if not alexa_result["plugin_enabled"]:
            self.logger.warn(
                "The Alexa Indigo Plugin is not enabled. "
                "The 'Ask a Yes/No Question' Device Action requires it.")

        # get value of Announcement Plugin subscription variable
        spoken_announcement_var = indigo.variables.get(
            self.subscription_variable)

        if self.pluginPrefs.get("enableSubscription", False):

            announcements_result = self.isPluginRunning("announcements")
            if announcements_result["plugin_enabled"]:

                if spoken_announcement_var is None:
                    indigo.variable.create(self.subscription_variable,
                                           value="", folder=None)
                    indigo.server.log(
                        f'The variable "{self.subscription_variable}" '
                        "was created")

                indigo.variables.subscribeToChanges()
                self.subscription_enabled = True

            else:
                self.logger.warn(
                    "The Announcements Plugin is not enabled. "
                    "Please enable it or uncheck 'Use Announcements' "
                    "in the Plugin Configuration Menu")
                self.subscription_enabled = False

        else:
            self.subscription_enabled = False

            if spoken_announcement_var:
                indigo.variable.delete(self.subscription_variable)
                indigo.server.log(
                    f'The variable "{self.subscription_variable}" '
                    "was deleted")

    def variableUpdated(self, orig_var, new_var):  # noqa
        indigo.PluginBase.variableUpdated(self, orig_var, new_var)

        if self.subscription_enabled:

            monitored_var = indigo.variables.get(self.subscription_variable)

            if monitored_var and monitored_var.value:

                if orig_var.id == monitored_var.id:

                    action = actionDict(
                        "text to speech", "TextToSpeech",
                        {"selectedVoice": self.selected_voice,
                         "ChangeVoice": self.change_voice,
                         "TextToSpeech": new_var.value})

                    # R19: this callback fires on EVERY variable change;
                    # a malformed announcingDevice pref must not traceback
                    try:
                        dev = indigo.devices.get(
                            int(self.announcing_device))
                    except (TypeError, ValueError):
                        dev = None
                    if dev:
                        self.text_to_speech(action, dev)
                    else:
                        self.logger.warn(
                            "The device configured to speak when the "
                            "'Speak Announcement' button is pressed, can "
                            "not be found.")
                    indigo.variable.updateValue(
                        self.subscription_variable, "")

            elif monitored_var is None:
                indigo.variable.create(self.subscription_variable,
                                       value="", folder=None)
                indigo.server.log(
                    f'The variable "{self.subscription_variable}" '
                    "was created")

            else:
                pass

    ########################################
    def shutdown(self):
        self.logger.debug("shutdown called")

    ########################################
    def deviceStartComm(self, dev):

        props = dev.pluginProps
        if dev.deviceTypeId == "VoiceMonkeyDevice":

            dev.updateStatesOnServer([
                {"key": "monkeyId", "value": props["monkey_id"]},
                {"key": "responseYesPresetId",
                    "value": props["yes_preset_id"]},
                {"key": "responseNoPresetId",
                    "value": props["no_preset_id"]},
                {"key": "useAltName", "value": props["useAltName"]},
                {"key": "altDeviceName", "value": props["AltDeviceName"]},
                {"key": "LastQuestionEpoch", "value": ""},
            ])

        elif dev.deviceTypeId == "AlexaRemoteControlDevice":
            props["SupportsBlueTooth"] = True
            if "monkey_id" in props:
                del props["monkey_id"]
            dev.replacePluginPropsOnServer(props)

    ##########################
    #  Run Concurrent Thread #
    ##########################
    def runConcurrentThread(self):
        try:
            while True:
                self.sleep(self.sleep_time)
                try:
                    self.questions.process_tick()
                except self.StopThread:
                    raise
                except Exception:
                    # R14: an unexpected tick failure must not kill this
                    # thread — that silently stops ALL Yes/No repeat and
                    # no-response processing until the plugin restarts.
                    self.logger.exception(
                        "Unexpected error while processing pending Yes/No "
                        "questions; continuing.")
        except self.StopThread:
            self.plugin_prefs["RepeatingYesNo"] = (
                self.questions.export_state())

    ##################################
    # Relay / Dimmer Action callback #
    ##################################
    def actionControlDevice(self, action, dev):

        if action.deviceAction == indigo.kDeviceAction.TurnOn:
            self.responseReceived("Yes", action, dev)

        elif action.deviceAction == indigo.kDeviceAction.TurnOff:
            self.responseReceived("No", action, dev)

        elif action.deviceAction == indigo.kDeviceAction.Toggle:
            new_on_state = not dev.onState
            self.logger.info(f'sent "{dev.name}" toggle')
            dev.updateStateOnServer("onOffState", new_on_state)

        else:
            self.logger.error(f"Unknown device action: {action.deviceAction}")

    ##################################
    def responseReceived(self, answer, action, dev):
        self.logger.debug("responseReceived called")

        # refetch, as legacy did
        dev = indigo.devices[action.deviceId]
        self.questions.handle_relay_action(answer, dev)

    ###########################
    # General Action callback #
    ###########################
    def actionControlUniversal(self, action, dev):

        if action.deviceAction == indigo.kUniversalAction.Beep:

            self.logger.info(f'sent "{dev.name}" beep request')
            # R4 FIX: legacy passed the display name 'Electronic Beep 1' where
            # a soundbank PATH is required, producing a malformed chime URL
            # (Beep silently failed). Pass the correct path.
            beep = actionDict("play a sound", "PlaySound",
                              {"soundName": "/musical/amzn_sfx_electronic_beep_01"})
            self.play_sound(beep, dev)

        elif action.deviceAction == indigo.kUniversalAction.RequestStatus:
            self.logger.info('sent "{}" status request'.format(dev.name))

            monkey_id = dev.states.get("monkeyId")
            last_question_epoch = dev.states.get("LastQuestionEpoch")
            yes_preset_id = dev.states.get("responseYesPresetId")
            no_preset_id = dev.states.get("responseNoPresetId")
            speech_overide = self.plugin_prefs.get("forTextToSpeech")

            if speech_overide:
                api_used = "Alexa Remote Control"
            else:
                api_used = "the Voice Monkey API"

            text_parts = [
                "This device, {}, is using {} for Text-to-Speech. ".format(
                    dev.name, api_used)
            ]

            if monkey_id:
                text_parts.append("A Monkey ID is configured. ")

            if not yes_preset_id and not no_preset_id:
                text_parts.append("The preset IDs for Yes and No responses "
                                  "are not configured. ")
            else:
                if yes_preset_id:
                    text_parts.append("The preset ID for Yes responses is "
                                      "set to {}. ".format(yes_preset_id))
                else:
                    text_parts.append("The preset ID for Yes responses is "
                                      "not configured. ")

                if no_preset_id:
                    text_parts.append("The preset ID for No responses is "
                                      "set to {}. ".format(no_preset_id))
                else:
                    text_parts.append("The preset ID for No responses is "
                                      "not configured. ")

            if last_question_epoch:
                if last_question_epoch == "Testing":
                    text_parts.append(
                        "The device is waiting for a Yes or No response "
                        "from a previously initiated test. ")
                else:
                    text_parts.append(
                        "The device is currently waiting for a Yes or No  "
                        "response from a recently asked question. ")

            use_alt_name = dev.states.get("useAltName", False)
            if use_alt_name:
                use_device_name = dev.states.get("altDeviceName", "")
                text_parts.append("An alternative device name is in use, "
                                  "that name is {}. ".format(use_device_name))

            action = actionDict("text to speech", "TextToSpeech",
                                {"TextToSpeech": "".join(text_parts)})

            if not self.validatePluginExecuteAction(action, dev):
                return False

            self.text_to_speech(action, dev)

    #####################################################################
    # Voice Monkey API Plugin Action callbacks (defined in Actions.xml) #
    #####################################################################

    def text_to_speech(self, plugin_action, dev):
        """TextToSpeech / SimpleSpeak"""
        self.logger.debug("text_to_speech called")

        # ARC override routing (legacy: only for UI descriptions)
        tts_routes = {
            "text to speech": self.alexa_speak,
            "simple speak": self.alexa_speak,
            "plugin action": False,   # do not over-ride script speech request
        }
        if self.plugin_prefs.get("forTextToSpeech"):
            action_fn = tts_routes.get(plugin_action.description)
            if action_fn:
                return action_fn(plugin_action, dev)

        if plugin_action.description == "plugin action":
            if not self.validatePluginExecuteAction(plugin_action, dev):
                return False

        if not self.monkey_validation(plugin_action, dev):
            return False

        prefix = (plugin_action.textToSpeak
                  if hasattr(plugin_action, "textToSpeak")
                  and plugin_action.textToSpeak else None)

        return actions.text_to_speech(
            self.vm_services, self._client(),
            dev.states["monkeyId"], dev.name,
            plugin_action.props.get("TextToSpeech", ""),
            change_voice=plugin_action.props.get("ChangeVoice", True),
            selected_voice=plugin_action.props.get("selectedVoice", False),
            prefix_text=prefix)

    ###########################################################
    def trigger_routine(self, plugin_action, dev=None):
        """TriggerRoutine"""
        self.logger.debug("trigger_routine called")

        if plugin_action.description == "plugin action":
            if not self.validatePluginExecuteAction(plugin_action, dev):
                return False

        if not self.monkey_validation(plugin_action, dev):
            return False

        return actions.trigger_routine(
            self.vm_services, self._client(),
            plugin_action.props["monkey_id"])

    ###########################################################
    def yes_no_question(self, plugin_action, dev):
        """YesNoQuestion"""
        self.logger.debug("yes_no_question called")

        which_device = plugin_action.props["whichDevice"]
        dev = indigo.devices.get(int(which_device))
        if not dev:
            self.logger.warn(
                "The device configured to ask the Yes/No question "
                "can no longer be found.")
            return False

        if plugin_action.description == "plugin action":
            if not self.validatePluginExecuteAction(plugin_action, dev):
                return False

        if not self.monkey_validation(plugin_action, dev):
            return False

        return self.questions.ask(plugin_action.props)

    ###########################################################
    def cancel_a_question(self, plugin_action, dev=None):
        """cancelQuestion"""
        self.logger.debug("cancel_a_question called")
        self.questions.cancel(
            plugin_action.props["question_to_cancel"],
            plugin_action.props["which_device"])

    ###########################################################
    def play_audio_file_url(self, plugin_action, dev):
        """PlayAudioFileUrl"""
        self.logger.debug("play_audio_file_url called")

        if plugin_action.description == "plugin action":
            if not self.validatePluginExecuteAction(plugin_action, dev):
                return False

        if not self.monkey_validation(plugin_action, dev):
            return False

        return actions.play_audio_file(
            self.vm_services, self._client(),
            dev.states["monkeyId"], dev.name,
            plugin_action.props.get("audioFileUrl"))

    ###########################################################
    def play_background_audio_file(self, plugin_action, dev):
        """PlayBackgroundAudioFile"""
        self.logger.debug("play_background_audio_file called")

        if plugin_action.description == "plugin action":
            if not self.validatePluginExecuteAction(plugin_action, dev):
                return False

        if not self.monkey_validation(plugin_action, dev):
            return False

        return actions.play_background_audio_file(
            self.vm_services, self._client(),
            dev.states["monkeyId"], dev.name,
            plugin_action.props.get("TextToSpeech", ""),
            plugin_action.props.get("backgroundAudioFileUrl"))

    ###########################################################
    def play_sound(self, plugin_action, dev):
        """PlaySound"""
        self.logger.debug("play_sound called")

        sound_value = plugin_action.props.get(
            "soundName", "/musical/amzn_sfx_test_tone_01")
        scripted = plugin_action.description == "plugin action"

        # ARC override (legacy: UI 'play a sound' only)
        if self.plugin_prefs.get("forPlayingSounds"):
            if plugin_action.description == "play a sound":
                self.alexa_play_sound(plugin_action, dev)
                return True
            elif scripted:
                if not self.validatePluginExecuteAction(plugin_action, dev):
                    return False

        if not self.monkey_validation(plugin_action, dev):
            return False

        return actions.play_sound(
            self.vm_services, self._client(),
            dev.states["monkeyId"], dev.name, sound_value, scripted=scripted)

    ###########################################################
    # alexa_remote_control callbacks (defined in Actions.xml) #
    ###########################################################
    def alexa_play_sound(self, plugin_action, dev):
        """PlaySound override via ARC"""
        self.logger.debug("alexa_play_sound called")

        the_sound = plugin_action.props.get("soundName")

        if plugin_action.description == "plugin action":
            if not self.validatePluginExecuteAction(plugin_action, dev):
                return False

        if dev.pluginProps["useAltName"]:
            the_device = dev.states["altDeviceName"]
        else:
            the_device = dev.name

        actions.alexa_play_sound(self.vm_services, self.arc,
                                 the_device, the_sound)

    ###########################################################
    def alexa_routine(self, plugin_action, dev=None):
        """AlexaRoutine"""
        self.logger.debug("alexa_routine called")
        self.logger.debug(f"{plugin_action.description}")

        if plugin_action.description == "plugin action":
            if not self.validatePluginExecuteAction(plugin_action, dev):
                return False

        if not self.monkey_validation(plugin_action, dev):
            return False

        the_routine = plugin_action.props["monkey_id"]

        if plugin_action.description == "plugin action":
            device_name = dev
        elif plugin_action.description == "run alexa routine by name":
            if dev.pluginProps["useAltName"]:
                device_name = dev.states["altDeviceName"]
            else:
                device_name = dev.name
        else:
            # R16: legacy fell through here to an unbound device_name
            # (NameError traceback); log string preserved, plus a clean exit.
            self.logger.error("Something went wrong")
            return False

        actions.alexa_routine(self.vm_services, self.arc,
                              device_name, the_routine)

    ###########################################################
    def alexa_speak(self, plugin_action, dev=None):
        """AlexaSpeak (hidden action / scripting)"""
        self.logger.debug("alexa_speak called")

        if plugin_action.description == "plugin action":
            if not self.validatePluginExecuteAction(plugin_action, dev):
                return False

        device_name = plugin_action.props.get("deviceName")

        if not device_name:
            if dev is None:
                self.logger.error(
                    u"Action has not been completely configured")
                return False
            elif dev.pluginProps.get("useAltName", False):
                device_name = dev.pluginProps["AltDeviceName"]
            else:
                device_name = dev.name

        prefix = (plugin_action.textToSpeak
                  if hasattr(plugin_action, "textToSpeak")
                  and plugin_action.textToSpeak else None)

        return actions.alexa_speak(
            self.vm_services, self.arc, device_name,
            plugin_action.props.get("TextToSpeech", ""),
            change_voice=plugin_action.props.get("ChangeVoice", True),
            selected_voice=plugin_action.props.get("selectedVoice"),
            prefix_text=prefix)

    ###########################################################
    def typed_request(self, plugin_action, dev):
        """TypedRequest"""
        self.logger.debug("typed_request called")

        if plugin_action.description == "plugin action":
            if not self.validatePluginExecuteAction(plugin_action, dev):
                return False

        if dev.pluginProps["useAltName"]:
            the_device = dev.states["altDeviceName"]
        else:
            the_device = dev.name

        actions.typed_request(self.vm_services, self.arc, the_device,
                              plugin_action.props.get("RequestOfDevice"))

    ###########################################################
    def pass_device_arg(self, plugin_action, dev):
        """PassDeviceArg"""
        self.logger.debug("pass_device_arg called")

        if plugin_action.description == "plugin action":
            if not self.validatePluginExecuteAction(plugin_action, dev):
                return False

        if dev.pluginProps["useAltName"]:
            device_name = dev.states["altDeviceName"]
        else:
            device_name = dev.name

        actions.pass_device_arg(self.vm_services, self.arc, device_name,
                                plugin_action.props.get("arguments"))

    ###########################################################
    def pass_cmd_line_args(self, plugin_action, dev):
        """PassArgs"""
        self.logger.debug("pass_cmd_line_args called")

        if plugin_action.description == "plugin action":
            if not self.validatePluginExecuteAction(plugin_action, dev):
                return False

        actions.pass_cmd_line_args(self.vm_services, self.arc,
                                   plugin_action.props.get("arguments"))

    #################################################
    # Functions Related to the Announcements Plugin #
    #################################################
    def refresh_fields(self, plugin_action, dev, something):
        """Dummy callback to force dynamic control refreshes."""
        self.logger.debug("refresh_fields")

    def announcement_speak_action(self, plugin_action, dev):
        """SpeakAnnouncements"""
        self.logger.debug("announcement_speak_action")

        announcements_plugin = indigo.server.getPlugin(self.announcements_pid)

        def export_announcements():
            return announcements_plugin.executeAction("exportAnnouncements")

        def refresh_announcement(announcement_name, source_id):
            announcements_plugin.executeAction(
                "refreshAnnouncementData", source_id,
                {"announcementToRefresh": announcement_name,
                 "announcementDeviceToRefresh": source_id})

        def speak(text, change_voice, selected_voice):
            action = actionDict("text to speech", "TextToSpeech",
                                {"selectedVoice": selected_voice,
                                 "ChangeVoice": change_voice,
                                 "TextToSpeech": text})
            self.text_to_speech(action, dev)

        services = announcements_bridge.AnnouncementsServices(
            is_plugin_running=lambda: self.isPluginRunning(
                "announcements")["plugin_enabled"],
            get_device=lambda dev_id: indigo.devices.get(dev_id),
            export_announcements=export_announcements,
            refresh_announcement=refresh_announcement,
            sleep=self.sleep,
            speak=speak,
            log_error=self.logger.error,
            log_warn=self.logger.warn,
            log_debug=self.logger.debug)

        return announcements_bridge.announcement_speak_action(
            services, plugin_action.props)

    ###########################################
    # Menu callbacks defined in MenuItems.xml #
    ###########################################
    def toggleDebugging(self):
        self.logger.debug("toggleDebugging called")

        if self.debug:
            self.logger.info("Turning off debug logging")
            self.plugin_prefs["showDebugInfo"] = False
        else:
            self.logger.info("Turning on debug logging")
            self.plugin_prefs["showDebugInfo"] = True
        self.debug = not self.debug

    ###########################################
    def cancel_question(self, valuesDict, typeId="", devId=None):
        """'Manage Yes/No Questions...' menu — cancel selected questions."""
        # R17: nothing selected (or key absent) must not TypeError
        questions = valuesDict.get("questions") or []
        for key in questions:

            try:
                action = self.questions.unanswered[key]["plugin_action"]
                question = action.get("QuestionToAsk")
                which_device = action["whichDevice"]

                dev = indigo.devices.get(int(which_device))
                if dev:
                    device_name = dev.name
                    last_question_epoch = dev.states["LastQuestionEpoch"]

                    if last_question_epoch == key:
                        dev.updateStatesOnServer([
                            {"key": "LastQuestionEpoch", "value": ""},
                        ])
                    del self.questions.unanswered[key]
                    log_entry = (
                        f"'{device_name}' pending question cancelled")
                    self.wrapLogging(f"{question}", log_entry)

                else:
                    self.logger.error(
                        "The configured device with the ID "
                        f'"{which_device}", no longer exists. ')

            except KeyError:
                self.logger.error(
                    f'The question key "{key}", no longer exists. ')

    ###########################################
    def show_pending_questions(self):
        self.questions.pending_summary()

    ###########################################
    def speech_test(self, valuesDict, typeId):
        self.logger.warn("'Speech Test' Button Pressed")

        device_id = valuesDict["whichDevice"]
        if device_id:
            # R18: the device can be deleted while the dialog is open
            dev = indigo.devices.get(int(device_id))
            if not dev:
                self.logger.error("The selected device no longer exists.")
                return
            if self.plugin_prefs.get("forTextToSpeech"):
                api_used = "Alexa Remote Control"
            else:
                api_used = "the Voice Monkey API"
            self.confirm_test(api_used, dev)

    ##########################################
    def yes_no_test(self, valuesDict, typeId):
        self.logger.warn("'Yes/No Test' Button Pressed")

        device_id = valuesDict["whichDevice"]
        if device_id:
            # R18: the device can be deleted while the dialog is open
            dev = indigo.devices.get(int(device_id))
            if not dev:
                self.logger.error("The selected device no longer exists.")
                return

            monkey_id = dev.states["monkeyId"]
            yes_preset_id = dev.states["responseYesPresetId"]
            no_preset_id = dev.states["responseNoPresetId"]

            question_to_ask = "Are you able to hear me clearly?"

            modified_text = (question_to_ask
                             .replace("\u2028", "")
                             .replace("\n", ""))
            substituted_text = self.substitute(modified_text)

            # R12 FIX: legacy fed random.choice() action groups into validation
            # (and crashed if none existed). Use a deterministic existing
            # group purely to satisfy validation; skip it when none exist.
            ag_keys = list(indigo.actionGroups.keys())
            if ag_keys:
                ask_yes_no = actionDict(
                    "ask a yes/no question", "YesNoQuestion",
                    {"whichDevice": device_id,
                     "QuestionToAsk": substituted_text,
                     "executeWhenYes": ag_keys[0],
                     "executeWhenNo": ag_keys[0]})
                if not self.validatePluginExecuteAction(ask_yes_no, dev):
                    return False
            else:
                self.logger.debug(
                    "No action groups exist; skipping test validation.")

            dev.updateStatesOnServer([
                {"key": "LastQuestionEpoch", "value": "Testing"},
            ])

            # ensure debugging is on during this test call (legacy)
            debug_temp = self.debug
            self.debug = True

            if self._client().ask_yes_no(monkey_id, substituted_text,
                                         yes_preset_id, no_preset_id):
                self.logger.warn(
                    f'Device Test: ({dev.name} "{question_to_ask}"')
            else:
                self.logger.error("That did not go so well.")

            self.debug = debug_temp

    ################################
    def confirm_test(self, answer, dev):

        if answer in ["Yes", "No"]:
            question = "Are you able to hear me clearly?"
            text_to_speak = (
                f"If you responded '{answer}' to the question, "
                f"'{question}' asked by {dev.name}, congrats, "
                "the test was successful. ")
        else:
            text_to_speak = (
                f"If you can hear this, your device, {dev.name}, "
                f"was able to generate speech using {answer}. "
                "Congrats!")

        action = actionDict("text to speech", "TextToSpeech",
                            {"TextToSpeech": text_to_speak})

        debug_temp = self.debug
        self.debug = True

        if not self.validatePluginExecuteAction(action, dev):
            return False

        self.text_to_speech(action, dev)

        self.debug = debug_temp

    ###############################################
    # Validation of Devices, Actions, Menus, etc. #
    ###############################################

    #####################
    # Device Validation #
    #####################
    def validateDeviceConfigUi(self, valuesDict, typeId, devId):
        self.logger.debug("Validating device config")

        errorsDict = indigo.Dict()

        def validate_monkey_id(valuesDict):
            monkey_id = valuesDict.get("monkey_id", "")
            useAltName = valuesDict.get("useAltName", False)
            if len(monkey_id) < 1:
                if not useAltName:
                    errorsDict["monkey_id"] = "Invalid Monkey ID entered"
                    self.logger.error(errorsDict["monkey_id"])
                    errorsDict["showAlertText"] = (
                        "What you should enter here, is the "
                        "name of the device you configured on "
                        "the Voice Monkey site. Click ? for "
                        "https://app.voicemonkey.io")

        def validate_device_name(valuesDict, devId):
            dev = indigo.devices[int(devId)]
            useAltName = valuesDict.get("useAltName", False)
            useCustomName = valuesDict.get("useCustomName", False)
            AltDeviceName = valuesDict.get("AltDeviceName", "")
            discoveredDevice = valuesDict.get("discoveredDevice", "")

            if useAltName:
                if discoveredDevice == "Default" or discoveredDevice == "":
                    valuesDict["AltDeviceName"] = AltDeviceName
                elif len(discoveredDevice) > 1:
                    valuesDict["AltDeviceName"] = discoveredDevice
                else:
                    valuesDict["AltDeviceName"] = dev.name

                if discoveredDevice == "Default" or discoveredDevice == "":
                    if len(AltDeviceName) < 1:
                        errorsDict["AltDeviceName"] = (
                            "An invalid device name was entered.")
                        self.logger.error(errorsDict["AltDeviceName"])
                        errorsDict["showAlertText"] = (
                            "You have to either select a discovered "
                            "device, or type in a custom device name.")
                    elif not useCustomName:
                        errorsDict["useAltName"] = (
                            "Invalid device name settings configuration.")
                        errorsDict["showAlertText"] = (
                            "No was name selected. Please uncheck "
                            "'Use an Alternate device'")
                elif useCustomName:
                    if len(AltDeviceName) > 1:
                        errorsDict["discoveredDevice"] = (
                            "An invalid device name was entered.")
                        errorsDict["AltDeviceName"] = (
                            "An invalid device name was entered.")
                        self.logger.error(errorsDict["AltDeviceName"])
                        errorsDict["showAlertText"] = (
                            "You have to either select a discovered "
                            "device, or type in a custom device name.")
            else:
                valuesDict["AltDeviceName"] = ""

        def validate_preset_ids(valuesDict):
            for preset in ["yes_preset_id", "no_preset_id"]:
                err_msg = (
                    "Please enter either numerical digits (1, 2, 3, etc.)"
                    " or the written words representing the numbers "
                    "(one, two, three, etc.). The correct value can be "
                    "found under API -> Presets Click '?' for "
                    "https://voicemonkey.io/ ")
                if valuesDict[preset]:
                    if valuesDict[preset].isdigit():
                        try:
                            a_preset_id = int(valuesDict[preset])
                            if a_preset_id < 1:
                                raise
                        except:  # noqa
                            errorsDict[preset] = "Invalid Preset IDs"
                            self.logger.error(errorsDict[preset])
                            errorsDict["showAlertText"] = err_msg
                    else:
                        if self._text2int(valuesDict[preset]):
                            valuesDict[preset] = self._text2int(
                                valuesDict[preset])
                        else:
                            errorsDict[preset] = "Invalid Preset IDs"
                            self.logger.error(errorsDict[preset])
                            errorsDict["showAlertText"] = err_msg
                else:
                    valuesDict[preset] = ""

        if typeId == "VoiceMonkeyDevice":
            validate_monkey_id(valuesDict)
            validate_preset_ids(valuesDict)
            validate_device_name(valuesDict, devId)

        if len(errorsDict) > 0:
            return (False, valuesDict, errorsDict)
        return (True, valuesDict)

    #####################
    # Action Validation #
    #####################
    def validateActionConfigUi(self, valuesDict, typeId, devId):
        self.logger.debug(
            f"Validating action config for type: {typeId} for {devId}")

        errorsDict = indigo.Dict()

        def validate_text_to_speech(valuesDict):
            change_voice = valuesDict.get("ChangeVoice", False)
            selected_voice = valuesDict.get("selectedVoice", None)

            if not change_voice:
                valuesDict["selectedVoice"] = None

            if selected_voice and selected_voice not in voices:
                errorsDict["selectedVoice"] = (
                    f"The voice '{selected_voice}' is not recognized")
                self.logger.error(errorsDict["selectedVoice"])

        def validate_play_audio_file_url(valuesDict):
            if not self.validateURL(valuesDict.get("audioFileUrl", "")):
                errorsDict["audioFileUrl"] = (
                    "Enter a publicly accessible URL. "
                    "The URL must begin with https://")
                errorsDict["showAlertText"] = errorsDict["audioFileUrl"]
                self.logger.error(errorsDict["audioFileUrl"])

        def validate_play_background_audio_file(valuesDict):
            if not self.validateURL(
                    valuesDict.get("backgroundAudioFileUrl", "")):
                errorsDict["backgroundAudioFileUrl"] = (
                    "Enter a publicly accessible URL. "
                    "The URL must begin with https://")
                errorsDict["showAlertText"] = errorsDict[
                    "backgroundAudioFileUrl"]
                self.logger.error(errorsDict["backgroundAudioFileUrl"])

        def validate_trigger_routine(valuesDict):
            if len(valuesDict.get("monkey_id", "")) < 1:
                errorsDict["monkey_id"] = (
                    "The 'monkey_id' is surely at least one character long")
                self.logger.error(errorsDict["monkey_id"])
                errorsDict["showAlertText"] = (
                    "This value can be found on voicemonkey.io, "
                    "under API -> Preset and is in the Monkey ID column")

        def validate_typed_request(valuesDict):
            RequestOfDevice = valuesDict.get("RequestOfDevice", "")
            if not self.plugin_prefs.get("AltModuleImported"):
                errorsDict["RequestOfDevice"] = (
                    "Additional configuration is required. "
                    "This is not a capability of the Voice Monkey API.")
                errorsDict["showAlertText"] = errorsDict["RequestOfDevice"]
                self.logger.error(errorsDict["RequestOfDevice"])

            if len(RequestOfDevice) < 1:
                errorsDict["RequestOfDevice"] = "You have to enter something."
                self.logger.error(errorsDict["RequestOfDevice"])
                errorsDict["showAlertText"] = (
                    "Type in your request, just as you would speak it to "
                    "your Alexa device. You don't need your wake word")

        def validate_alexa_routine(valuesDict):
            monkey_id = valuesDict.get("monkey_id", "")
            if not self.plugin_prefs.get("AltModuleImported"):
                errorsDict["monkey_id"] = (
                    "Additional configuration is required. "
                    "This is not a capability of the Voice Monkey API.")
                errorsDict["showAlertText"] = errorsDict["monkey_id"]
                self.logger.error(errorsDict["monkey_id"])

            if len(monkey_id) < 1:
                errorsDict["monkey_id"] = "You have to enter something."
                self.logger.error(errorsDict["monkey_id"])
                errorsDict["showAlertText"] = (
                    "Type in your EXACT name of your Alexa Routine, as shown "
                    "in the Alexa App.")

        def validate_pass_args(valuesDict):
            arguments = valuesDict.get("arguments", "")
            if not self.plugin_prefs.get("AltModuleImported"):
                errorsDict["arguments"] = (
                    "Additional configuration is required. "
                    "This is not a capability of the Voice Monkey API.")
                errorsDict["showAlertText"] = errorsDict["arguments"]
                self.logger.error(errorsDict["arguments"])

            if len(arguments) < 1:
                errorsDict["arguments"] = "No arguments specified."
                self.logger.error(errorsDict["arguments"])
                errorsDict["showAlertText"] = (
                    "Type in arguments that you want to send to your "
                    "Alexa device(s). Click '?' for available commands.")

        def validate_device(valuesDict):
            which_device = valuesDict.get("whichDevice", 0)
            if which_device:
                try:
                    smart_device = indigo.devices[int(which_device)]
                    response_preset_ids = ["responseYesPresetId",
                                           "responseNoPresetId"]
                    for preset_id in response_preset_ids:
                        if not smart_device.states.get(preset_id):
                            err_msg = (
                                "The selected device is not configured "
                                "for Yes or No questions")
                            self.logger.error(err_msg)
                            errorsDict["QuestionToAsk"] = err_msg
                            errorsDict["showAlertText"] = (
                                "You cannot ask Yes or No questions on the "
                                "selected device because it is not "
                                "configured to respond. "
                                "To change the device settings, find the "
                                "device in the device table, double-click "
                                "it (or select it an click the Edit… "
                                "button) and then choose 'Edit Device "
                                "Settings'. Once there, enter the "
                                "appropriate values for the Yes and No "
                                "Preset IDs.")
                            break
                except KeyError:
                    err_msg = ("Please select the Device that asks "
                               "the question.")
                    self.logger.error(err_msg)
                    errorsDict["whichDevice"] = err_msg
                    errorsDict["showAlertText"] = errorsDict["whichDevice"]
            else:
                err_msg = "Please select the Device that asks the question."
                self.logger.error(err_msg)
                errorsDict["whichDevice"] = err_msg
                errorsDict["showAlertText"] = err_msg

        def validate_action_groups(valuesDict):
            execute_when_no = valuesDict.get("executeWhenNo", False)
            execute_when_yes = valuesDict.get("executeWhenYes", False)

            if execute_when_no == "0":
                execute_when_no = False
            if execute_when_yes == "0":
                execute_when_yes = False

            no_response_group = valuesDict.get("noResponseActionGroup", 0)
            execute_no_response = bool(valuesDict.get("executeNoResponse",
                                                      False))

            if not execute_when_yes and not execute_when_no:
                err_msg = ("You have to select a Action Group to Execute "
                           "for at least one response, Yes or No")
                self.logger.error(err_msg)
                errorsDict["executeWhenYes"] = err_msg
                errorsDict["executeWhenNo"] = err_msg
                errorsDict["showAlertText"] = err_msg
            else:
                for yes_or_no in ["executeWhenYes", "executeWhenNo"]:
                    action_group = valuesDict.get(yes_or_no, False)
                    if (action_group
                            and not self.validate_action_group_id(
                                action_group)):
                        err_msg = ("A valid Action Group is needed for "
                                   "either the Yes or No response.")
                        self.logger.error(err_msg)
                        errorsDict[yes_or_no] = err_msg
                        errorsDict["showAlertText"] = err_msg

            if execute_no_response:
                if no_response_group:
                    if no_response_group == "0":
                        no_response_group = None
                        valuesDict["noResponseActionGroup"] = (
                            no_response_group)
                    elif self.validate_action_group_id(no_response_group):
                        valuesDict["noResponseActionGroup"] = int(
                            no_response_group)
                    else:
                        err_msg = (
                            "You must select a valid Action Group "
                            "to be executed, if the option is ticked.")
                        errorsDict["noResponseActionGroup"] = err_msg
                        errorsDict["showAlertText"] = err_msg
                        self.logger.error(err_msg)
                else:
                    err_msg = (
                        "You must select a valid Action Group "
                        "to be executed, if the option is ticked.")
                    errorsDict["noResponseActionGroup"] = err_msg
                    errorsDict["showAlertText"] = err_msg
                    self.logger.error(err_msg)

        def validate_repeat_settings(valuesDict):
            cycles = int(valuesDict.get("cycles", 2))
            seconds = int(valuesDict.get("seconds", 35))

            if valuesDict.get("RepeatQuestion", False):
                cycles_error = ("If you enter 2, you will hear the question "
                                "twice. The minimum is 2 times.")
                seconds_error = ("In order to have enough time to respond. "
                                 "The minimum time between questions is "
                                 f"{self.min_delay} seconds.")

                if cycles < 2:
                    self.logger.error(cycles_error)
                    errorsDict["cycles"] = cycles_error
                    errorsDict["showAlertText"] = cycles_error

                if seconds < self.min_delay:
                    self.logger.error(seconds_error)
                    errorsDict["seconds"] = seconds_error
                    errorsDict["showAlertText"] = seconds_error

        def validate_yes_no_question(valuesDict):
            result = self.isPluginRunning("alexa")
            if not result["plugin_enabled"]:
                err_msg = "The Indigo Alexa plugin is not enabled."
                errorsDict["QuestionToAsk"] = err_msg
                self.logger.error(err_msg)
                errorsDict["showAlertText"] = (
                    "To implement 'Ask a Yes/No Question', you have "
                    "to Enable the Indigo Alexa plugin.")

            question_to_ask = valuesDict.get("QuestionToAsk", "")
            if not question_to_ask:
                err_msg = (
                    "The question you want to ask has an invalid format")
                self.logger.error(err_msg)
                errorsDict["QuestionToAsk"] = err_msg
                errorsDict["showAlertText"] = err_msg

        def validate_cancelQuestion(valuesDict):
            which_device = valuesDict.get("which_device", "0")
            question_to_cancel = valuesDict.get("question_to_cancel", "")

            if not which_device.isdigit():
                errorsDict["which_device"] = (
                    "Please select the device which asks the question "
                    "you want to cancel.")
                self.logger.error(errorsDict["which_device"])
                errorsDict["showAlertText"] = errorsDict["which_device"]

            if len(question_to_cancel) < 1:
                errorsDict["question_to_cancel"] = (
                    "You must type in the EXACT text of the Yes/No "
                    "Question, in order to cancel it. TIP: Use copy & "
                    "paste.")
                self.logger.error(errorsDict["question_to_cancel"])
                errorsDict["showAlertText"] = errorsDict[
                    "question_to_cancel"]

        def validate_announcements(valuesDict):
            result = self.isPluginRunning("announcements")
            if not result["plugin_enabled"]:
                err_msg = "The Announcements Plugin is not enabled. "
                errorsDict["Announcements"] = err_msg
                self.logger.error(err_msg)
                errorsDict["showAlertText"] = (
                    "To use 'Speak Announcements', you have "
                    "to Enable the Announcements plugin.")

            source_id = valuesDict["theAnnouncement"]
            announcementToSpeak = valuesDict["announcementToSpeak"]

            if not source_id.isdigit():
                err_msg = "Please select a Source."
                errorsDict["theAnnouncement"] = err_msg
                self.logger.error(err_msg)
                errorsDict["showAlertText"] = err_msg

            elif indigo.devices[int(source_id)].model == "Announcements Device":  # noqa

                plugin = indigo.server.getPlugin(self.announcements_pid)
                result = plugin.executeAction("exportAnnouncements")
                all_announcements = json.loads(result)

                announcements = all_announcements[source_id]

                modified_name = announcementToSpeak.replace("_", " ")
                matching_items = [v for k, v in announcements.items()
                                  if v["Name"] == modified_name]
                announcement_message = (matching_items[0]["Announcement"]
                                        if matching_items else None)

                if announcement_message is None:
                    err_msg = "Announcement not found"
                    errorsDict["announcementToSpeak"] = err_msg
                    self.logger.error(err_msg)
                    errorsDict["showAlertText"] = err_msg

                elif re.search(r"\[\[.*?\]\]",
                                             announcement_message):
                    err_msg = (
                        "This Plugin is unable to interpret the "
                        "embedded speech commands in the selected "
                        "announcement.")
                    errorsDict["announcementToSpeak"] = err_msg
                    self.logger.error(err_msg)
                    errorsDict["showAlertText"] = err_msg

            else:
                if len(announcementToSpeak) < 1:
                    err_msg = "Please select an Item to Speak."
                    errorsDict["announcementToSpeak"] = err_msg
                    self.logger.error(err_msg)
                    errorsDict["showAlertText"] = err_msg

        if typeId == "PlayBackgroundAudioFile":
            validate_play_background_audio_file(valuesDict)
            validate_text_to_speech(valuesDict)
        elif typeId == "PlayAudioFileUrl":
            validate_play_audio_file_url(valuesDict)
        elif typeId == "YesNoQuestion":
            validate_yes_no_question(valuesDict)
            validate_repeat_settings(valuesDict)
            validate_action_groups(valuesDict)
            validate_device(valuesDict)
        elif typeId == "cancelQuestion":
            validate_cancelQuestion(valuesDict)
        elif typeId == "TriggerRoutine":
            validate_trigger_routine(valuesDict)
        elif typeId == "TextToSpeech":
            validate_text_to_speech(valuesDict)
        elif typeId == "TypedRequest":
            validate_typed_request(valuesDict)
        elif typeId == "AlexaRoutine":
            validate_alexa_routine(valuesDict)
        elif typeId == "PassArgs":
            validate_pass_args(valuesDict)
        elif typeId == "PassDeviceArg":
            validate_pass_args(valuesDict)
        elif typeId == "SpeakAnnouncements":
            validate_announcements(valuesDict)
        else:
            self.logger.debug(f"unaccounted for: {typeId}")

        if len(errorsDict) > 0:
            return (False, valuesDict, errorsDict)
        return (True, valuesDict)

    ###########################
    # PluginConfig Validation #
    ###########################
    def validatePrefsConfigUi(self, valuesDict):
        self.logger.debug("validatePrefsConfigUi called")

        errorsDict = indigo.Dict()

        def validate_tokens_pref(valuesDict):
            access_token = valuesDict.get("accessToken", "")
            secret_token = valuesDict.get("secretToken", "")

            if not (len(access_token) >= 1 and len(secret_token) >= 1):
                if valuesDict.get("useAlexaRemoteControl", False):
                    self.logger.warn(
                        "To use any function that requires the Voice "
                        "Monkey API, such as audio playback ")
                    self.logger.warn(
                        "or verbally prompted 'Yes or No' questions, "
                        "API Tokens are required.")
                    self.logger.warn(
                        "The imported 'alexa_remote_control' module can "
                        " handle text-to-speech and sound playback, if "
                        "it is set up and configured correctly.")
                else:
                    errorMsg = (
                        "Voice Monkey API Tokens are not configured "
                        "correctly")
                    errorsDict["accessToken"] = errorMsg
                    errorsDict["secretToken"] = errorMsg
                    errorsDict["showAlertText"] = (
                        "To use the Voice Monkey API, you must "
                        "enter both your Secret and Access Tokens")

        def validate_api_version_pref(valuesDict):
            # ADDITIVE: v3 is scaffold-only; allow selecting it but warn
            if valuesDict.get("apiVersion", "v2") == "v3":
                self.logger.warn(
                    "Voice Monkey API v3 is scaffolded but not implemented "
                    "or verified yet. All API actions will fail until v3 "
                    "support lands. Set the API version back to v2.")

        def validate_announcements_pref(valuesDict):
            enable_subscription = valuesDict.get("enableSubscription", False)
            announcing_device = valuesDict.get("announcingDevice", False)
            change_voice = valuesDict.get("ChangeVoice", False)
            selected_voice = valuesDict.get("selectedVoice", False)

            if enable_subscription:

                result = self.isPluginRunning("announcements")
                if not result["plugin_enabled"]:
                    errorMsg = ("The Announcements Plugin is not enabled. "
                                "It is required to use Variable "
                                "Subscription.")
                    errorsDict["enableSubscription"] = errorMsg
                    errorsDict["showAlertText"] = errorMsg

                elif not announcing_device:
                    errorMsg = ("Please select a device to speak when you "
                                "the 'Speak Announcement' button within "
                                "the Announcements plugin is pressed")
                    errorsDict["announcingDevice"] = errorMsg
                    errorsDict["showAlertText"] = errorMsg
                else:
                    self.announcing_device = announcing_device

                if not change_voice:
                    self.selected_voice = None
                elif selected_voice and selected_voice not in voices:
                    errorsDict["selectedVoice"] = (
                        f"The voice '{selected_voice}' is not recognized")
                    errorsDict["showAlertText"] = (
                        errorsDict["selectedVoice"])
                elif not selected_voice:
                    errorsDict["selectedVoice"] = (
                        "Please select a voice or uncheck "
                        "'Change the Voice?'")
                    errorsDict["showAlertText"] = (
                        errorsDict["selectedVoice"])
                else:
                    self.selected_voice = selected_voice
                    self.change_voice = change_voice

            else:
                self.announcing_device = False
                self.selected_voice = None
                self.change_voice = False
                valuesDict["ChangeVoice"] = False

        def validate_yesno_timing_pref(valuesDict):
            adjust_timing = valuesDict.get("AdjustTiming", False)
            if adjust_timing:
                try:
                    max_time_to_wait = int(valuesDict.get("maxTimeToWait"))
                    if max_time_to_wait < 5:
                        raise ValueError("maxTimeToWait must be at least 5.")
                except (ValueError, TypeError) as e:
                    self.logger.debug(str(e))
                    errorMsg = ("Invalid entry, a positive number greater "
                                "than 5 was not entered")
                    errorsDict["maxTimeToWait"] = errorMsg
                    errorsDict["showAlertText"] = (
                        "The maximum number of seconds to wait for a "
                        "Yes or No response must be a positive number "
                        "greater than 5.")
                else:
                    self.max_wait = max_time_to_wait

                try:
                    min_yes_no_delay = int(valuesDict.get("minYesNoDelay"))
                    if min_yes_no_delay < 5:
                        raise ValueError("minYesNoDelay must be at least 5.")
                except (ValueError, TypeError) as e:
                    self.logger.debug(str(e))
                    errorMsg = ("Invalid entry, a positive number greater "
                                "than 5 was not entered")
                    errorsDict["minYesNoDelay"] = errorMsg
                    if "showAlertText" not in errorsDict:
                        errorsDict["showAlertText"] = (
                            "The minimum number of seconds that must "
                            "elapse before a question can be repeated, "
                            "must be a positive number greater than 5")
                    else:
                        errorsDict["showAlertText"] += (
                            " Also, the minimum number of seconds for "
                            "minYesNoDelay must be greater than 5.")
                else:
                    self.min_delay = min_yes_no_delay

                try:
                    sleep_time = int(valuesDict.get("sleepTime"))
                    if sleep_time < 1:
                        raise ValueError("sleepTime cannot be less than 1.")
                except (ValueError, TypeError) as e:
                    self.logger.debug(str(e))
                    errorMsg = "Invalid entry, value cannot be less than 1."
                    errorsDict["sleepTime"] = errorMsg
                    if "showAlertText" not in errorsDict:
                        errorsDict["showAlertText"] = (
                            "Specify the number of seconds to pause "
                            "between iterations of the "
                            "runConcurrentThread() function by entering a "
                            "value in the text field. The default value "
                            "is 5 seconds.")
                    else:
                        errorsDict["showAlertText"] += (
                            " Also, the sleepTime must be a positive "
                            "number and cannot be less than 1.")
                else:
                    self.sleep_time = sleep_time

            else:
                self.min_delay = 35
                self.max_wait = 30
                self.sleep_time = 5
                valuesDict["minYesNoDelay"] = 35
                valuesDict["maxTimeToWait"] = 30
                valuesDict["sleepTime"] = 5

        def validate_alexa_remote_control_pref(valuesDict):
            # upstream behavior restored (was drift-forced False; see __init__)
            use_alexa_remote = valuesDict.get("useAlexaRemoteControl", False)

            if use_alexa_remote:
                errorMsg = (
                    "Additional configuration is required "
                    "before this selection is allowed. See "
                    "the documenation for more information.")
                if not self.plugin_prefs.get("AltModuleImported"):
                    errorsDict["showAlertText"] = errorMsg
                    errorsDict["use_alexa_remote"] = errorMsg
            else:
                valuesDict["forTextToSpeech"] = False
                valuesDict["forPlayingSounds"] = False

        def configure_debug_pref(valuesDict):
            show_debug_messages = valuesDict.get("showDebugInfo", False)
            self.debug = show_debug_messages
            if show_debug_messages:
                self.logger.info("debug logging is on")
            else:
                self.logger.info("debug logging is off")

        def validate_logging_pref(valuesDict):
            try:
                self.max_combined_length = int(valuesDict.get(
                    "maxCombinedLength", 150))
                if self.max_combined_length < 25:
                    raise ValueError(
                        "maxCombinedLength must be at least 25.")
            except (ValueError, TypeError) as e:
                self.logger.debug(str(e))
                errorMsg = ("Invalid entry, a positive number greater than "
                            "25 was not entered for the character length.")
                errorsDict["maxCombinedLength"] = errorMsg
                errorsDict["showAlertText"] = (
                    "The minimum character value for maxCombinedLength is "
                    "25. The default was 150.")

            try:
                self.max_text_length = int(valuesDict.get(
                    "maxTextLength", 150))
                if self.max_text_length < 25:
                    raise ValueError("maxTextLength must be at least 25.")
            except (ValueError, TypeError) as e:
                self.logger.debug(str(e))
                errorMsg = ("Invalid entry, a positive number greater than "
                            "25 was not entered for the character length.")
                errorsDict["maxTextLength"] = errorMsg
                if "showAlertText" not in errorsDict:
                    errorsDict["showAlertText"] = (
                        "The minimum character value for maxTextLength is "
                        "25. The default was 150.")
                else:
                    errorsDict["showAlertText"] += (
                        " Also, the minimum character value for "
                        "maxTextLength is 25. The default was 150.")

        validate_tokens_pref(valuesDict)
        validate_api_version_pref(valuesDict)
        validate_announcements_pref(valuesDict)
        validate_yesno_timing_pref(valuesDict)
        validate_alexa_remote_control_pref(valuesDict)
        configure_debug_pref(valuesDict)
        validate_logging_pref(valuesDict)

        # keep the question manager in sync with (possibly changed) timing
        self.questions.max_wait = self.max_wait

        if len(errorsDict) > 0:
            return (False, valuesDict, errorsDict)
        return (True, valuesDict)

    ####################
    # Config UI Closed #
    ####################
    def closedPrefsConfigUi(self, valuesDict, userCancelled):
        self.logger.debug("closedPrefsConfigUi called")

        if self.subscription_enabled != valuesDict.get("enableSubscription",
                                                       False):
            indigo.server.log("Preparing to restart plugin...")
            self.restartPlugin(message="", isError=False)

    ####################
    # Event Validation #
    ####################
    def validateEventConfigUi(self, valuesDict, typeId, eventId):
        pass

    ######################################################
    def validatePluginExecuteAction(self, plugin_action, dev):
        self.logger.debug("validatePluginExecuteAction called")

        if isinstance(dev, indigo.RelayDevice):
            device_id = dev.id
        else:
            device_id = dev

        return self.validateActionConfigUi(plugin_action.props,
                                           plugin_action.pluginTypeId,
                                           device_id)[0]

    ######################################################
    def validate_action_group_id(self, ag_id):
        self.logger.debug("validate_action_group_id called")

        if not ag_id:
            return True

        try:
            if int(ag_id) == 0:
                return True
            if indigo.actionGroups[int(ag_id)]:
                return True
        except (KeyError, ValueError):
            # R15: a DELETED group raises KeyError from
            # indigo.actionGroups[id], which the legacy 'except ValueError'
            # never caught — the error message below was unreachable and
            # validation crashed with a traceback instead. Non-numeric IDs
            # (ValueError, previously raised outside the try) land here too.
            self.logger.error(
                f'The previously configured Action Group ID "{ag_id}"", '
                "no longer exists. Was it deleted?")
            return False

    ###########################################################
    def monkey_validation(self, plugin_action, dev=None):
        self.logger.debug("monkey_validation called")

        access_token = self.plugin_prefs.get("accessToken")
        secret_token = self.plugin_prefs.get("secretToken")

        if isinstance(dev, indigo.RelayDevice):
            props = dev.pluginProps
            monkey_id = props.get("monkey_id", None)
        else:
            monkey_id = plugin_action.props.get("monkey_id")

        if plugin_action.pluginTypeId == "YesNoQuestion":
            result = self.isPluginRunning("alexa")
        else:
            result = None

        errors = {
            "accessToken": "To use the Monkey Voice API, you must configure "
                           "an Access Token.",
            "secretToken": "To use the Monkey Voice API, you must configure "
                           "a Secret Token.",
            "monkey_id": "The Voice Monkey functions are not fully "
                         "configured for this device.",
            "alexa_enabled": "The Alexa Indigo Plugin is not enabled. "
                             "The 'Ask a Yes/No Question' Device Action "
                             "requires it."
        }
        error_fields = []
        for field, message in errors.items():
            if field == "accessToken":
                if not access_token:
                    error_fields.append(field)
                    self.logger.error(message)
            elif field == "secretToken":
                if not secret_token:
                    error_fields.append(field)
                    self.logger.error(message)
            elif field == "monkey_id":
                if monkey_id is None or len(monkey_id) < 1:
                    error_fields.append(field)
                    self.logger.error(message)
            elif field == "alexa_enabled":
                if result is not None and not result["plugin_enabled"]:
                    error_fields.append(field)
                    self.logger.error(message)
        return not bool(error_fields)

    ################################
    # Dynamic lists and generators #
    ################################
    def questionList(self, filter="", valuesDict=None, typeId="", targetId=0):  # noqa
        values = []
        for key in self.questions.unanswered.keys():
            which_device = (
                self.questions.unanswered[key]["plugin_action"]
                ["whichDevice"])
            # R3 FIX: legacy indexed indigo.devices[...] and raised KeyError
            # when the device had been deleted while its question was pending
            dev = indigo.devices.get(int(which_device))
            question = (self.questions.unanswered[key]["plugin_action"]
                        ["QuestionToAsk"])

            question_to_ask = (question
                               .replace("\u2028", "")
                               .replace("\n", ""))

            label = dev.name if dev else f"(missing device {which_device})"
            values.append((key, f"{label} - {question_to_ask}"))
        return values

    def deviceList(self, dev_filter=None):
        devices_list = [("None", "None")]
        devices_list.extend((dev.id, dev.name)
                            for dev in indigo.devices.iter(dev_filter))
        return devices_list

    def announcement_devices(self, filter="", valuesDict=None, typeId="", targetId=0):  # noqa
        return self.deviceList(self.announcements_pid)

    @staticmethod
    def generator_announcement_list(filter="", values_dict=None, type_id="", target_id=0):  # noqa
        try:
            announcement_id = int(values_dict["theAnnouncement"])
            if announcement_id in indigo.devices:
                result = [
                    (state, state.replace("_", " "))
                    for state in indigo.devices[announcement_id].states
                    if "onOffState" not in state
                ]
            else:
                result = [("value", "Value")]
        except KeyError:
            result = [("None", "None")]
        except ValueError:
            result = [("None", "None")]

        return result

    def myListGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):  # noqa
        if self.plugin_prefs.get("AltModuleImported", False):
            return self.arc.list_available_devices()
        return [("Default", "")]

    def myActionGroupList(self, filter="", valuesDict=None, typeId="", targetId=0):  # noqa
        pluginId = "com.anyone.indigoplugin.voice-monkey"
        devices = [dev.id for dev in indigo.devices.iter(pluginId)]

        device_action_list = []
        for device in devices:
            data = indigo.device.getDependencies(device)
            for entry in data["actionGroups"]:
                device_action_list.append((entry["ID"], entry["Name"]))

        if device_action_list:
            return sorted(device_action_list, key=lambda x: x[1])
        else:
            return [("Default", "")]

    def voicesList(self, filter="", valuesDict=None, typeId="", targetId=0):  # noqa
        return [(name, description) for name, description in voices.items()]

    def soundsList(self, filter="", valuesDict=None, typeId="", targetId=0):  # noqa
        return [(path, name) for path, name in sounds.items()]

    def actionsWithAnExit(self, filter="", valuesDict=None, typeId="", targetId=0):  # noqa
        action_group_list = [(ag.id, ag.name) for ag in indigo.actionGroups]
        sorted_list = sorted(action_group_list, key=lambda x: x[1].lower())
        sorted_list.insert(0, (0, "- select an action group -"))
        return sorted_list if sorted_list else [(0, "")]

    def find_by_action(self, ID):
        devices = []
        for dev in indigo.devices.iter("self"):
            devices.append(dev.id)

        device_action_list = []
        for device in devices:
            data = indigo.device.getDependencies(device)
            for entry in data["actionGroups"]:
                device_action_list.append(
                    (entry["ID"], entry["Name"], device))

        for id, name, device in device_action_list:
            if id == ID:
                return device

    ###########################
    # Miscellaneous Functions #
    ###########################
    def isPluginRunning(self, plugin_name):
        plugin_names = {
            "alexa":
            {"plugin_id": "com.indigodomo.indigoplugin.alexa"},
            "announcements":
            {"plugin_id": self.announcements_pid},
        }

        plugin_id = plugin_names[plugin_name]["plugin_id"]
        plugin = indigo.server.getPlugin(plugin_id)
        plugin_enabled = plugin.isEnabled()

        return {"plugin_enabled": plugin_enabled}

    def wrapLogging(self, substituted_text, log_entry):
        for line in format_wrapped_log(substituted_text, log_entry,
                                       self.max_combined_length,
                                       self.max_text_length):
            indigo.server.log(line)

    ###########################
    def validateURL(self, url):
        regex = ("^((https)://)[-a-zA-Z0-9@:%._\\+~#?&//=]{2,256}"
                 "\\.[a-z]{2,6}\\b([-a-zA-Z0-9@:%._\\+~#?&//=]*)$")

        substituted_url = self.substitute(url)
        r = re.compile(regex)
        if re.search(r, substituted_url):
            return True
        else:
            return False

    ###########################
    @staticmethod
    def _text2int(textnum, numwords={}):
        units = [
            "zero", "one", "two", "three", "four", "five", "six", "seven",
            "eight", "nine", "ten", "eleven", "twelve", "thirteen",
            "fourteen", "fifteen", "sixteen", "seventeen", "eighteen",
            "nineteen",
        ]
        tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty",
                "seventy", "eighty", "ninety"]
        scales = ["hundred", "thousand", "million", "billion", "trillion"]
        numwords["and"] = (1, 0)
        for idx, word in enumerate(units):
            numwords[word] = (1, idx)
        for idx, word in enumerate(tens):
            numwords[word] = (1, idx * 10)
        for idx, word in enumerate(scales):
            numwords[word] = (10 ** (idx * 3 or 2), 0)
        current = result = 0
        cleaned_textnum = textnum.replace("-", " ")
        for word in cleaned_textnum.split():
            if word not in numwords:
                return

            scale, increment = numwords[word]
            current = current * scale + increment
            if scale > 100:
                result += current
                current = 0
        return result + current
