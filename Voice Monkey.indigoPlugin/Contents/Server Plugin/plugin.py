#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################

import re
import json
import indigo
import random
import requests
import textwrap
from urllib.parse import quote
from urllib.parse import quote_plus  
from alexa_constants import voices, sounds
from datetime import datetime, timedelta

try:
    import alexa_remote_control
    WAS_IMPORTED = True
    indigo.server.log('alexa_remote_control was imported')
except ImportError:
    WAS_IMPORTED = False


###########################
class actionDict():
    def __init__(self, description, pluginTypeId, props):
        self.description = description
        self.pluginTypeId = pluginTypeId
        self.props = props


################################
class Plugin(indigo.PluginBase):
    
    def __init__(self, plugin_id, plugin_display_name, plugin_version, plugin_prefs):  # noqa
        super().__init__(plugin_id, plugin_display_name, plugin_version, plugin_prefs) # noqa

        # retain the configurable logging state
        self.debug = plugin_prefs.get("showDebugInfo", False)

        # configurable setting for Yes/No Question Promptng
        self.sleep_time = int(plugin_prefs.get("sleepTime", 5))
        self.min_delay = int(plugin_prefs.get("minYesNoDelay", 35))
        self.max_wait = int(plugin_prefs.get("maxTimeToWait", 30))

        # dict of all active unanswered Yes/No questions questions
        self.unanswered = plugin_prefs.get("RepeatingYesNo", indigo.Dict())

        # configurable setting for output to the log
        self.max_text_length = plugin_prefs.get("maxTextLength", 150)
        self.max_combined_length = plugin_prefs.get("maxCombinedLength", 150)

        # determine if alexa_remote_control was imported
        self.plugin_prefs["AltModuleImported"] = WAS_IMPORTED

        # define the variable updated by the Announcements Plugin
        self.subscription_variable = "spoken_announcement_raw"

        # store the Announcements Plugin's Id
        self.announcements_pid = 'com.fogbert.indigoplugin.announcements'

        # define the device used to speak when using the Announcements Plugin
        self.announcing_device = self.plugin_prefs.get('announcingDevice', 0)

        # device voice to use with the Announcements Plugin
        self.change_voice = self.plugin_prefs.get('ChangeVoice', False)
        self.selected_voice = self.plugin_prefs.get('selectedVoice', False)

    ########################################
    def startup(self):
        self.logger.debug("startup called")

        # show pending questions on startup
        self.show_pending_questions()

        # check if the Alexa Plugin is running
        alexa_result = self.isPluginRunning('alexa')
        if not alexa_result["plugin_enabled"]:
            self.logger.warn(
                       "The Alexa Indigo Plugin is not enabled. "
                       "The 'Ask a Yes/No Question' Device Action requires it."
                       )

        # get value of Announcement Plugin subscription variable
        spoken_announcement_var = indigo.variables.get(
                                            self.subscription_variable)

        # determine if variable subscription is enabled
        if self.pluginPrefs.get('enableSubscription', False):

            # check if the Announcements Plugin is running
            announcements_result = self.isPluginRunning('announcements')
            if announcements_result["plugin_enabled"]:

                # Check if "spoken_announcement_raw" variable does NOT exist
                if spoken_announcement_var is None:
                    # Create "spoken_announcement_raw" variable
                    indigo.variable.create(self.subscription_variable, 
                                           value="", 
                                           folder=None)
                    indigo.server.log(
                        f'The variable "{self.subscription_variable}" '
                        'was created')

                # subscribe to variable changes
                indigo.variables.subscribeToChanges()

                # update subscription state
                self.subscription_enabled = True

            else:  # the Announcements Plugin is NOT running

                self.logger.warn(
                           "The Announcements Plugin is not enabled. "
                           "Please enable it or uncheck 'Use Announcements' "
                           "in the Plugin Configuration Menu"
                           )
                # update subscription state
                self.subscription_enabled = False

        else:  # variable subscription is disabled

            # update subscription state
            self.subscription_enabled = False

            # Check if "spoken_announcement_raw" variable exists
            if spoken_announcement_var:
                # delete variable
                indigo.variable.delete(self.subscription_variable)
                indigo.server.log(
                    f'The variable "{self.subscription_variable}" '
                    'was deleted')


    def variableUpdated(self, orig_var, new_var):  # noqa
        """
        Triggers a text-to-speech announcement when the monitored variable 
        is changed.
        
        Args:
            orig_var (indigo.Variable): The original variable object.
            new_var (indigo.Variable): The new variable object.
        """

        # Call the parent implementation of variableUpdated() base class
        indigo.PluginBase.variableUpdated(self, orig_var, new_var)

        # If "Subscribe to Changes" is enabled
        if self.subscription_enabled:

            # Check if "spoken_announcement_raw" variable exists
            monitored_var = indigo.variables.get(self.subscription_variable)

            # if variable we are monitoring exists and it has some value
            if monitored_var and monitored_var.value:

                # If "spoken_announcement_raw" variable changed
                if orig_var.id == monitored_var.id:

                    # prepare what is to be spoken
                    action = actionDict('text to speech', 
                                        'TextToSpeech',
                                        {"selectedVoice": self.selected_voice,
                                         "ChangeVoice": self.change_voice,
                                         "TextToSpeech": new_var.value})

                    # ensure speak announcement device exists
                    dev = indigo.devices.get(int(self.announcing_device))
                    if dev:
                        self.text_to_speech(action, dev)
                    else:
                        self.logger.warn(
                            "The device configured to speak when the "
                            "'Speak Announcement' button is pressed, can "
                            "not be found."
                            )
                    # clear out the variable
                    indigo.variable.updateValue(
                                    self.subscription_variable, "")

            # if equal to None, variable doesn't exists
            elif monitored_var is None:
                # Create "spoken_announcement_raw" variable
                indigo.variable.create(self.subscription_variable, 
                                       value="", 
                                       folder=None)
                indigo.server.log(
                    f'The variable "{self.subscription_variable}" '
                    'was created')

            else:  # ignore
                pass

    ########################################
    def shutdown(self):
        self.logger.debug("shutdown called")

    ########################################
    def deviceStartComm(self, dev):

        props = dev.pluginProps
        if dev.deviceTypeId == 'VoiceMonkeyDevice':

            # clear the device states used by Yes/No
            dev.updateStatesOnServer([
                {'key': 'monkeyId', 
                    'value': props["monkey_id"]},
                {'key': 'responseYesPresetId', 
                    'value': props["yes_preset_id"]},
                {'key': 'responseNoPresetId', 
                    'value': props["no_preset_id"]},                
                {'key': 'useAltName', 
                    'value': props["useAltName"]},                
                {'key': 'altDeviceName', 
                    'value': props["AltDeviceName"]},
                {'key': 'LastQuestionEpoch', 'value': ''}, 
            ])

        # can be removed, no devices of this types exist yet
        elif dev.deviceTypeId == 'AlexaRemoteControlDevice':
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

                number_unanswered = len(self.unanswered)
                if number_unanswered > 0:

                    epoch_run_time = datetime.now().timestamp()
                    expired_keys = (
                        key for key, value in self.unanswered.items()
                        if epoch_run_time - value['tracking']['timestamp'] 
                        > self.max_wait 
                        or ('delayed' in value['tracking'] 
                            and value['tracking']['delayed'])
                    )
                    for key in sorted(expired_keys):
                        self.process_expired_key(key, epoch_run_time)

        except self.StopThread:
            self.plugin_prefs["RepeatingYesNo"] = self.unanswered

    ##########################
    def process_expired_key(self, key, epoch_run_time):

        # dictionary key access
        tracking = self.unanswered[key]['tracking']
        plugin_action = self.unanswered[key]['plugin_action']

        # assign values
        the_count = tracking['count']
        time_stamp = tracking['timestamp']
        delayed = tracking.get('delayed', False)
        cycles = int(plugin_action.get('cycles', 0))
        seconds = int(plugin_action.get('seconds', 0))
        question_to_ask = plugin_action.get('QuestionToAsk')
        question_text = self.substitute(question_to_ask)
        which_device = plugin_action.get('whichDevice')
        repeats = plugin_action.get('RepeatQuestion', False)
        stop_when_no = plugin_action.get('StopWhenNo', True)
        stop_when_yes = plugin_action.get('StopWhenYes', True)
        no_response = plugin_action.get('noResponseActionGroup', None)
        execute_no_response = plugin_action.get('executeNoResponse', False)

        # prepare for display, perform substituion and remove line feeds
        question = self.substitute(question_to_ask)
        question_text = (question.replace('\u2028', "").replace('\n', ""))

        dev = indigo.devices.get(int(which_device))
        if not dev:
            del self.unanswered[key]
            return

        if delayed:
            # try to ask the question again
            action = actionDict('ask a yes/no question', 
                                'YesNoQuestion',
                                plugin_action)
            self.yes_no_question(action, dev)
            return

        if repeats:
            if time_stamp + int(seconds) < epoch_run_time:
                if the_count < int(cycles):
                    action = actionDict('ask a yes/no question', 
                                        'YesNoQuestion',
                                        plugin_action)
                    self.yes_no_question(action, dev)
                    return
                else:
                    try:
                        if execute_no_response:
                            exit_when = ('Yes' if stop_when_yes 
                                         else 'No' if stop_when_no 
                                         else 'Yes or No')
                            text = (
                                f"{question_text}"
                                )
                            log_entry = (
                                f"'{dev.name}' did not receive a "
                                f"'{exit_when}' response after "
                                f"repeating"
                                )
                            self.wrapLogging(text, log_entry)

                            indigo.actionGroup.execute(int(no_response))
                        else:
                            exit_when = ('Yes' if stop_when_yes 
                                         else 'No' if stop_when_no 
                                         else 'Yes or No')
                            text = (
                                f"{question_text}"
                                )
                            log_entry = (
                                f"'{dev.name}' did not receive a "
                                f"'{exit_when}' response after repeating"
                                )
                            self.wrapLogging(text, log_entry)
                    except ValueError:
                        self.logger.warn(
                            'The Action Group configured to '
                            'execute when a Yes or No response '
                            'is not received, can not be found.')
                    del self.unanswered[key]
            elif dev.states['LastQuestionEpoch'] == key:
                text = (
                    f"{question_text}"
                    )
                log_entry = (
                    f"'{dev.name}' did not receive a "
                    f"'Yes' or 'No' response to"
                    )
                self.wrapLogging(text, log_entry)
        else:
            try:
                del self.unanswered[key]
                if execute_no_response:
                    self.logger.info(
                        f"'{dev.name}' did not receive a "
                        "response. Executing the 'No Response'"
                        " action group.")
                    indigo.actionGroup.execute(int(no_response))
                elif dev.states['LastQuestionEpoch'] == key:
                    text = (
                        f"{question_text}"
                        )
                    log_entry = (
                        f"'{dev.name}' did not receive a "
                        f"'Yes' or 'No' response to"
                        )
                    self.wrapLogging(text, log_entry)
            except ValueError:
                self.logger.warn(
                    'The Action Group configured to execute '
                    'when a Yes or No response is not  '
                    'received, can not be found.')

        if dev.states['LastQuestionEpoch'] == key:
            # inside the For Loop, clear device states
            dev.updateStatesOnServer([
                {'key': 'LastQuestionEpoch', 'value': ''}, 
            ])

    ##################################
    # Relay / Dimmer Action callback #
    ##################################
    def actionControlDevice(self, action, dev):

        ###### TURN ON ####### noqa 
        if action.deviceAction == indigo.kDeviceAction.TurnOn:
            self.responseReceived('Yes', action, dev)

        ###### TURN OFF ####### noqa 
        elif action.deviceAction == indigo.kDeviceAction.TurnOff:
            self.responseReceived('No', action, dev)

        ###### TOGGLE ####### noqa 
        elif action.deviceAction == indigo.kDeviceAction.Toggle:

            # determine the opposite states
            new_on_state = not dev.onState

            # If success then log that the command was successfully sent.
            self.logger.info(f'sent "{dev.name}" toggle')

            # And then tell the Indigo Server to update the state
            dev.updateStateOnServer("onOffState", new_on_state)

        else:  # Anything not implemented

            self.logger.error(f"Unknown device action: {action.deviceAction}")

    ##################################
    def responseReceived(self, answer, action, dev):

        self.logger.debug("responseReceived called")

        # get current device states
        dev = indigo.devices[action.deviceId]
        last_question_epoch = dev.states['LastQuestionEpoch']

        # match the response to the unanswered questions list
        if self.unanswered.get(last_question_epoch, False):

            self.logger.debug(f'\n{self.unanswered[last_question_epoch]}')

            last_action = self.unanswered[last_question_epoch]['plugin_action']
            last_tracking = self.unanswered[last_question_epoch]['tracking']
            the_count = last_tracking['count']
            cycles = last_action.get('cycles', 0)
            seconds = last_action.get('seconds', 0)
            repeats = last_action.get('RepeatQuestion', False)

            yes_on_action_group = last_action.get('executeWhenYes', False)
            off_no_action_group = last_action.get('executeWhenNo', False)

            if repeats:
                m, s = divmod(int(seconds), 60)
                if m == 0:
                    time_string = f"{s} seconds"
                else:
                    time_string = f"{m} minutes, {s} seconds"

            if answer == 'Yes':
                exit_on_answer = last_action.get(
                    "StopWhenYes", True)
                response_action_group = yes_on_action_group
                message_prefix = f"'{dev.name}' received a 'Yes' response."
            else:  # 'No'
                exit_on_answer = last_action.get(
                    "StopWhenNo", True)
                response_action_group = off_no_action_group
                message_prefix = f"'{dev.name}' received a 'No' response."

            # an action group was not picked by the user or not passed
            if response_action_group and response_action_group != '0':
                
                message = (f"{message_prefix}")

                if exit_on_answer:
                    if repeats:
                        message += (
                            " The question will not be asked again.")
                    del self.unanswered[last_question_epoch]
                elif repeats and int(cycles) > int(the_count):
                    message += (" The question will be repeated "
                                f"in {time_string}.")
                elif repeats and int(cycles) <= int(the_count):
                    message += " The question will not be repeated."
                    del self.unanswered[last_question_epoch]
                else:
                    del self.unanswered[last_question_epoch]

                try:
                    self.logger.info(message)
                    indigo.actionGroup.execute(int(response_action_group))

                except ValueError:
                    self.logger.critical(
                        f"The Action Group configured for a '{answer}' "
                        "response cannot be found."
                    )
                    del self.unanswered[last_question_epoch]
            else:
                message = (f"{message_prefix} A response is "
                           "not configured.")
                if exit_on_answer:
                    if repeats:
                        message += (
                            " The question will not be asked again.")
                    del self.unanswered[last_question_epoch]
                elif repeats and int(cycles) > int(the_count):
                    message += (" The question will be repeated in "
                                f"{time_string}.")
                else:
                    if repeats:
                        message += " The question will not be repeated."
                    del self.unanswered[last_question_epoch]

                self.logger.info(message)

            # clear out the device states, for the next question
            dev.updateStatesOnServer([
                {'key': 'onOffState', 'value': False},
                {'key': 'LastQuestionEpoch', 'value': ''}, 
            ])

        else:  # not found in unanswered questions

            if last_question_epoch == "Testing":
                self.confirm_test(answer, dev)

                # clear out the device states, for the next question
                dev.updateStatesOnServer([
                    {'key': 'onOffState', 'value': False},
                    {'key': 'LastQuestionEpoch', 'value': ''}, 
                ])

            elif answer == "Yes":

                dev.updateStateOnServer("onOffState", True)

            elif answer == "No":

                dev.updateStateOnServer("onOffState", False)

    ###########################
    # General Action callback #
    ###########################

    def actionControlUniversal(self, action, dev):

        ###### BEEP ####### noqa 
        if action.deviceAction == indigo.kUniversalAction.Beep:

            # Beep the hardware module (dev) here:
            self.logger.info(f'sent "{dev.name}" beep request')

            beep = actionDict('play a sound', 
                              'PlaySound',
                              {"soundName": "Electronic Beep 1"})
            self.play_sound(beep, dev)

        ###### STATUS REQUEST ####### noqa 
        elif action.deviceAction == indigo.kUniversalAction.RequestStatus:
            # Query hardware module (dev) for its current status here:
            self.logger.info('sent "{}" status request'.format(dev.name))

            monkey_id = dev.states.get("monkeyId")
            last_question_epoch = dev.states.get("LastQuestionEpoch")
            yes_preset_id = dev.states.get("responseYesPresetId")
            no_preset_id = dev.states.get("responseNoPresetId")
            no_preset_id = dev.states.get("responseNoPresetId")
            speech_overide = self.plugin_prefs.get("forTextToSpeech")

            if speech_overide:
                api_used = "Alexa Remote Control"
            else:
                api_used = 'the Voice Monkey API'

            text_parts = [
                'This device, {}, is using {} for Text-to-Speech. '.format(
                    dev.name, api_used)
            ]

            if monkey_id:
                text_parts.append('A Monkey ID is configured. ')

            if not yes_preset_id and not no_preset_id:
                text_parts.append('The preset IDs for Yes and No responses '
                                  'are not configured. ')
            else:
                if yes_preset_id:
                    text_parts.append('The preset ID for Yes responses is '
                                      'set to {}. '.format(yes_preset_id))
                else:
                    text_parts.append('The preset ID for Yes responses is '
                                      'not configured. ')

                if no_preset_id:
                    text_parts.append('The preset ID for No responses is '
                                      'set to {}. '.format(no_preset_id))
                else:
                    text_parts.append('The preset ID for No responses is '
                                      'not configured. ')

            if last_question_epoch:
                if last_question_epoch == 'Testing':
                    text_parts.append(
                        'The device is waiting for a Yes or No response '
                        'from a previously initiated test. ')
                else:
                    text_parts.append(
                        'The device is currently waiting for a Yes or No  '
                        'response from a recently asked question. ')

            use_alt_name = dev.states.get("useAltName", False)
            if use_alt_name:
                use_device_name = dev.states.get("altDeviceName", "")
                text_parts.append('An alternative device name is in use, '
                                  'that name is {}. '.format(use_device_name))

            action = actionDict('text to speech', 
                                'TextToSpeech',
                                {"TextToSpeech": ''.join(text_parts)})

            # validate Action Config for scripting
            if not self.validatePluginExecuteAction(action, dev):
                return False

            # call with predefine tone
            self.text_to_speech(action, dev)

    #####################################################################
    # Voice Monkey API Plugin Action callbacks (defined in Actions.xml) #
    #####################################################################

    def text_to_speech(self, plugin_action, dev):
        """
        This function converts Text-to-Speech on a device
        
        Passed to it is the Text, a Monkey ID and a device
        TextToSpeech
        """

        # announce function if debugging
        self.logger.debug("text_to_speech called")

        # if over-riding how Speech is handled
        actions = {
            'text to speech': self.alexa_speak,
            'simple speak': self.alexa_speak,
            'plugin action': False,  # do not over-ride script speech request
        }
        if self.plugin_prefs.get('forTextToSpeech'):
            action_fn = actions.get(plugin_action.description)
            if action_fn:
                return action_fn(plugin_action, dev)

        if plugin_action.description == "plugin action":
            # validate Action Config for scripting
            if not self.validatePluginExecuteAction(plugin_action, dev):
                return False

        # check if a Monkey and tokens are fully configured
        if not self.monkey_validation(plugin_action, dev):
            return False

        # where to say it
        monkey_id = dev.states['monkeyId']

        # what to say
        if hasattr(plugin_action, 'textToSpeak') and plugin_action.textToSpeak:
            text_to_speech = (f'{plugin_action.textToSpeak} '
                              f'{plugin_action.props.get("TextToSpeech", "")}')
        else:
            text_to_speech = plugin_action.props.get("TextToSpeech", "")

        # if there is nothing to speak
        if text_to_speech.isspace() or len(text_to_speech) == 0:
            self.logger.error(u"Action has not been completely configured")
            text_to_speech = ("No announcement text specified. Please update "
                              "the action to replace this message.")

        # what voice to use
        selected_voice = plugin_action.props.get("selectedVoice", False)

        # remove newline characters
        modified_text = (text_to_speech
                         .replace('\u2028', "")
                         .replace('\n', ""))        

        # perform Indigo variable substitution 
        substituted_text = self.substitute(modified_text)

        # replace "&" with "&amp;" for SSML compatibility 
        ssml_text = substituted_text.replace("&", "&amp;")

        # build payload
        payload = {
                   "monkey_name": "-".join(monkey_id.lower().split()),
                   "say_this": quote(ssml_text)
                   }

        # build url
        query = ('&monkey={monkey_name}&announcement={say_this}')

        # if voice change checkbox ticked, defaults to True for scripting
        if plugin_action.props.get("ChangeVoice", True):
            if selected_voice:
                query += f'&voice={selected_voice}'
                selected_voice_info = (
                    f'{voices.get(selected_voice)}')
            else:
                selected_voice_info = 'Alexa - Default'
        else:
            selected_voice_info = 'Alexa - Default'

        log_entry = f'{dev.name} : Text-to-Speech : {selected_voice_info}'

        # make request and display to log if successful
        if self.make_request(query, payload):

            self.wrapLogging(substituted_text, log_entry)
            return True
        else:
            return False     

    ###########################################################
    def trigger_routine(self, plugin_action, dev=None):
        """
        This function triggers a preset monkey ID to execute an Alexa Routine.
        
        Passed to it is the Monkey ID/Preset Monkey ID and a device 
        TriggerRoutine
        """

        # announce function if debugging
        self.logger.debug("trigger_routine called")

        if plugin_action.description == "plugin action":
            # validate Action Config for scripting
            if not self.validatePluginExecuteAction(plugin_action, dev):
                return False

        # check if a Monkey and tokens are fully configured
        if not self.monkey_validation(plugin_action, dev):
            return False

        # get the Voice Monkey Preset Monkey ID (ex. routine-trigger-one)
        monkey_name = plugin_action.props['monkey_id']

        # build the payload
        payload = {"monkey_name": "-".join(monkey_name.lower().split())}
        
        # build url
        query = ('&monkey={monkey_name}')

        if (self.make_request(query, payload)):

            indigo.server.log(
                f'Trigger a Routine : "{monkey_name}"'
                )
            return True
        else:
            return False

    ###########################################################
    def yes_no_question(self, plugin_action, dev):
        """
        This function uses Text-to-Speech to ask a Yes or No prompted Question 
        on a given device.
        
        Passed to it is Question, and a Action Group id to be executed if the  
        response is Yes, Action Group id to be executed if the response 
        is No and one to execute if response is not given

        YesNoQuestion
        """

        # announce function if debugging
        self.logger.debug("yes_no_question called")

        # get the device info
        which_device = plugin_action.props["whichDevice"]
        dev = indigo.devices.get(int(which_device))
        if not dev:
            self.logger.warn(
                "The device configured to ask the Yes/No question "
                "can no longer be found."
                )
            return False

        # if running as script
        if plugin_action.description == "plugin action":
            # validate variables passed by scripting
            if not self.validatePluginExecuteAction(plugin_action, dev):
                return False

        # check if a Monkey and tokens are fully configured
        if not self.monkey_validation(plugin_action, dev):
            return False

        # get epoch time
        new_run_time = datetime.now().timestamp()
        new_epoch_string = f'T{new_run_time}'

        # check if key is in the unanswered list
        key = self.find_props(plugin_action.props)
        
        if key:
            self.logger.debug(f'key: {key}')

            # is the device waiting for an answer
            if dev.states['LastQuestionEpoch'] not in ['', 'Testing']:
                # a previous question is active, try again later
                return

            # update the question in the unanswered list
            tracking = self.unanswered[key]['tracking']
            actions = self.unanswered[key]['plugin_action']
            count = tracking['count']
            cycles = actions['cycles']

            # if final pass, change seconds, to evaluated no response sooner
            if (count + 1) >= int(cycles):
                actions['seconds'] = self.max_wait
                self.unanswered.setitem_in_item(key, 'plugin_action', actions)

            tracking['count'] = count + 1
            tracking['timestamp'] = new_run_time
            tracking['delayed'] = False

            self.unanswered.setitem_in_item(key, 'tracking', tracking)

            # update the device states
            dev.updateStatesOnServer([
                {'key': 'LastQuestionEpoch', 'value': key}, 
            ])

        else:  # update list with a new key
         
            self.logger.debug(f'new key created: {key}')

            # create a secondary dictionary item
            tracking = indigo.Dict()
            tracking['timestamp'] = new_run_time

            # set tracking count based on device status
            if dev.states['LastQuestionEpoch'] in ['', 'Testing']:
                tracking['count'] = 1
                tracking['delayed'] = False

            else:  # the device is waiting for a response
                tracking['count'] = 0
                tracking['delayed'] = True

                # combine the two dictionary items
                new_entry = indigo.Dict()
                new_entry['plugin_action'] = plugin_action.props
                new_entry['tracking'] = tracking
                self.unanswered[new_epoch_string] = new_entry
                return  # try again later 
    
            # combine the two dictionary items
            new_entry = indigo.Dict()
            new_entry['tracking'] = tracking
            new_entry['plugin_action'] = plugin_action.props

            # prepare for the response
            self.unanswered[new_epoch_string] = new_entry
            dev.updateStatesOnServer([
                {'key': 'LastQuestionEpoch', 'value': new_epoch_string}, 
            ])

        # What to ask
        question_to_ask = plugin_action.props["QuestionToAsk"]

        # remove newline characters
        modified_text = (question_to_ask
                         .replace('\u2028', "")
                         .replace('\n', ""))

        # perform Indigo variable substitution 
        substituted_text = self.substitute(modified_text)

        # replace "&" with "&amp;" for SSML compatibility
        ssml_text = substituted_text.replace("&", "&amp;")

        # get values for Voice Monkey 
        monkey_id = dev.pluginProps["monkey_id"]
        no_preset_id = dev.pluginProps["no_preset_id"]
        yes_preset_id = dev.pluginProps["yes_preset_id"]
            
        # build payload for Voice Monkey
        payload = {
                   "monkey_name": "-".join(monkey_id.lower().split()),
                   "ask_this": quote(ssml_text),
                   "yes_preset": yes_preset_id,
                   "no_preset": no_preset_id
                   }

        # build API GET request
        query = (
               '&monkey={monkey_name}'
               '&announcement={ask_this}'
               '&prompt-yes-preset={yes_preset}'
               '&prompt-no-preset={no_preset}'
               )

        log_entry = f'{dev.name} : Asked a Yes/No Question'

        # make request and display to log if successful
        if self.make_request(query, payload):

            self.wrapLogging(substituted_text, log_entry)

            # if string substitution is in use
            if substituted_text != modified_text:
                self.logger.debug(f'Unmodified_text: {modified_text}')

            return True
        else:
            return False     

    ###########################################################
    def cancel_a_question(self, plugin_action, dev=None):
        """
        This function cancels the Yes or No Question entered.
        
        Passed to it is the Yes or No Question, it cycles thru all of 
        the unanswers questions and cancels the one which matches the
        text of the question entered and device

        cancelQuestion
        """        
        self.logger.debug("cancel_a_question called")

        # the name of the Yes/No question to cancel
        question_to_cancel = plugin_action.props['question_to_cancel']
        cancel_question_on_device = plugin_action.props['which_device']

        # loop thru the unanswered questions
        for key in self.unanswered.keys():

            action = self.unanswered[key]['plugin_action']
            question_to_ask = action.get('QuestionToAsk')
            asking_device = action['whichDevice']

            # look for a match
            if (question_to_cancel == question_to_ask 
               and str(cancel_question_on_device) == asking_device):

                # if voice monkey device exists
                dev = indigo.devices.get(int(asking_device))
                if dev:

                    # if the question was just asked
                    if dev.states['LastQuestionEpoch'] == key:
                        # clear the device state 
                        dev.updateStatesOnServer([
                            {'key': 'LastQuestionEpoch', 'value': ''}, 
                        ])

                    # delete the question
                    del self.unanswered[key]

                    # format the log entry
                    log_entry = (
                        f'Succesfully Canceled Yes/No Question : {dev.name}')

                    # remove special characters
                    modified_text = (question_to_ask
                                     .replace('\u2028', "")
                                     .replace('\n', ""))

                    self.wrapLogging(self.substitute(modified_text), log_entry)

                    break
                    
                else:
                    self.logger.error(
                      'The device asking the question, no longer exists. ')

        else:  # match not found

            dev = indigo.devices.get(int(cancel_question_on_device))
            if dev:

                # remove special characters
                modified_text = (question_to_cancel
                                 .replace('\u2028', "")
                                 .replace('\n', ""))
                # warn the user
                self.logger.warn(
                    'Cancel failed, no matching Yes/No Question found : '
                    f'{dev.name} : "{modified_text}"')

            else:
                self.logger.error(
                  'The device asking the question, no longer exists. ')

    ###########################################################
    def play_audio_file_url(self, plugin_action, dev):
        """

        PlayAudioFileUrl
        """
        self.logger.debug("play_audio_file_url called")

        # if running as script
        if plugin_action.description == "plugin action":

            # validate Action Config for scripting
            if not self.validatePluginExecuteAction(plugin_action, dev):
                return False

        # check if a Monkey and tokens are fully configured
        if not self.monkey_validation(plugin_action, dev):
            return False

        # where to play it
        monkey_id = dev.states['monkeyId']

        # which sound to make
        audio_file_url = plugin_action.props.get("audioFileUrl")

        # remove newline characters
        modified_url = (audio_file_url
                        .replace('\u2028', "")
                        .replace('\n', ""))

        # perform Indigo variable substitution 
        substituted_url = self.substitute(modified_url)

        payload = {
                   "monkey_name": "-".join(monkey_id.lower().split()),
                   "audio": quote_plus(substituted_url)
                   }

        query = (
               '&monkey={monkey_name}'
               '&announcement=%20'
               '&audio={audio}'
               '')

        if self.make_request(query, payload):
            indigo.server.log(
                f'{dev.name}: Play a Audio File: "{substituted_url}"'
                )
            return True
        else:
            return False

    ###########################################################
    def play_background_audio_file(self, plugin_action, dev):
        """

        PlayBackgroundAudioFile
        """

        self.logger.debug("play_background_audio_file called")

        # if running as script
        if plugin_action.description == "plugin action":

            # validate Action Config for scripting
            if not self.validatePluginExecuteAction(plugin_action, dev):
                return False

        # check if a Monkey and tokens are fully configured
        if not self.monkey_validation(plugin_action, dev):
            return False

        # where to play it
        monkey_id = dev.states['monkeyId']

        # which sound to make
        audio_file_url = plugin_action.props.get("backgroundAudioFileUrl")

        # remove newline characters
        modified_url = (audio_file_url
                        .replace('\u2028', "")
                        .replace('\n', ""))

        # perform Indigo variable substitution 
        substituted_url = self.substitute(modified_url)

        # what to say
        text_to_speech = plugin_action.props.get("TextToSpeech", "")

        # remove newline characters
        modified_text = (text_to_speech
                         .replace('\u2028', "")
                         .replace('\n', ""))

        # perform Indigo variable substitution 
        substituted_text = self.substitute(modified_text)

        # replace "&" with "&amp;" for SSML compatibility
        ssml_text = substituted_text.replace("&", "&amp;")

        payload = {
                   "monkey_name": "-".join(monkey_id.lower().split()),
                   "bkg-audio": quote_plus(substituted_url),
                   "text_to_speech": quote(ssml_text)
                   }

        # build API GET request
        query = (
               '&monkey={monkey_name}'
               '&announcement={text_to_speech}'
               '&bkg-audio={bkg-audio}'
               ''
               )

        url_log_entry = f'{dev.name}: Play Background Audio File'
        log_entry = f'{dev.name} : Text-to-speech'
        
        if self.make_request(query, payload):
            self.wrapLogging(substituted_url, url_log_entry)
            self.wrapLogging(substituted_text, log_entry)

            return True
        else:
            return False

    ###########################################################
    def play_sound(self, plugin_action, dev):
        """

        PlaySound
        """
        self.logger.debug("play_sound called")

        # where to play it
        monkey_id = dev.states['monkeyId']

        # get the name of the sound
        sound_path = plugin_action.props.get("soundName", 
                                             '/musical/amzn_sfx_test_tone_01')
        # get the path of the sound to make
        the_sound = sounds.get(sound_path, 'Tone 1') 

        # if scripting
        if plugin_action.description == "plugin action":
            the_sound = sound_path
            sound_path = next((key for key, value in sounds.items() 
                              if value == sound_path), None)
            sound_path = str(sound_path) if sound_path is not None else ""                          

        # if over-riding how sounds are played
        if self.plugin_prefs.get("forPlayingSounds"):
            if plugin_action.description == 'play a sound':
                self.alexa_play_sound(plugin_action, dev)
                return True

            # if running as script
            elif plugin_action.description == "plugin action":

                # validate plugin_action
                if not self.validatePluginExecuteAction(plugin_action, dev):
                    return False

        # check if a Monkey and tokens are fully configured
        if not self.monkey_validation(plugin_action, dev):
            return False

        # build payload
        payload = {
                   "monkey_name": "-".join(monkey_id.lower().split()),
                   "chime": quote_plus("soundbank://soundlibrary{0}".
                                       format(sound_path))
                   }

        # build url
        query = (
               '&monkey={monkey_name}'
               '&announcement=%20'
               '&chime={chime}'
               '')

        if self.make_request(query, payload):
            indigo.server.log(
                f'{dev.name}: Play a Sound : "{the_sound}"'
                )
            return True
        else:
            return False

    ###########################################################
    # alexa_remote_control callbacks (defined in Actions.xml) #
    ###########################################################
    def alexa_play_sound(self, plugin_action, dev):
        """

        PlaySound
        """

        self.logger.debug("alexa_play_sound called")

        # get the name of the sound
        the_sound = plugin_action.props.get("soundName")

        if plugin_action.description == "plugin action":
            # validate Action Config for scripting
            if not self.validatePluginExecuteAction(plugin_action, dev):
                return False

        # if use wants to use an alternate name
        if dev.pluginProps["useAltName"]:
            the_device = dev.states['altDeviceName']
        else:  # otherwise use the device name
            the_device = dev.name
    
        # if something to be said
        alexa_remote_control.alexa_play_sound(the_sound, 
                                              the_device, 
                                              )
        
    ###########################################################
    def alexa_routine(self, plugin_action, dev=None):
        """
        This function executes an Alexa Routine by name.
        
        Passed to it is the device and Routine name. 
        
        AlexaRoutine

        """

        # announce function if debugging
        self.logger.debug("alexa_routine called")
        self.logger.debug(f"{plugin_action.description}")

        # input not validated

        if plugin_action.description == "plugin action":
            # validate Action Config for scripting
            if not self.validatePluginExecuteAction(plugin_action, dev):
                return False

        # check if a Monkey and tokens are fully configured
        if not self.monkey_validation(plugin_action, dev):
            return False

        # use the Routine Name provide, should be as in the Alexa App
        the_routine = plugin_action.props['monkey_id']

        # determine the device name if not passed
        if plugin_action.description == "plugin action":
            device_name = dev 

        elif plugin_action.description == "run alexa routine by name":

            # if user wants to use an alternate name
            if dev.pluginProps["useAltName"]:
                device_name = dev.states['altDeviceName']
            else:  # otherwise use the device name
                device_name = dev.name
        else:
            self.logger.error('Something went wrong')

        # if something to be said
        alexa_remote_control.alexa_routine(the_routine, 
                                           device_name, 
                                           )

    ###########################################################
    def alexa_speak(self, plugin_action, dev=None):
        """
        This function converts Text-to-Speech
        
        Passed it the Text, a Monkey ID, device and optionally a voice name

        Action: AlexaSpeak
        """

        # announce function if debugging
        self.logger.debug("alexa_speak called")

        if plugin_action.description == "plugin action":
            # validate Action Config for scripting
            if not self.validatePluginExecuteAction(plugin_action, dev):
                return False

        # get device name passed by script, if any, names not validated...
        device_name = plugin_action.props.get("deviceName")

        # if no device name passed in from scripting, determine the device name
        if not device_name:

            if dev is None:
                self.logger.error(u"Action has not been completely configured")
                return False

            # check if user wants to use an alternate name
            elif dev.pluginProps.get("useAltName", False):
                device_name = dev.pluginProps["AltDeviceName"]
            else:  
                # otherwise use the default device name
                device_name = dev.name

        # what to say
        if hasattr(plugin_action, 'textToSpeak') and plugin_action.textToSpeak:
            text_to_speech = (f'{plugin_action.textToSpeak} '
                              f'{plugin_action.props.get("TextToSpeech", "")}')
        else:
            text_to_speech = plugin_action.props.get("TextToSpeech", "")

        if text_to_speech.isspace():
            self.logger.error(u"Action has not been completely configured")
            return False

        # remove newline characters
        modified_text = (text_to_speech
                         .replace('\u2028', "")
                         .replace('\n', ""))

        # perform Indigo variable substitution 
        substituted_text = self.substitute(modified_text)

        # replace "&" with "&amp;" for SSML compatibility
        ssml_text = substituted_text.replace("&", "&amp;")

        # if voice change checkbox ticked
        if plugin_action.props.get("ChangeVoice", True):
            selected_voice = plugin_action.props.get("selectedVoice")
            if selected_voice:
                selected_voice_info = (f'{voices.get(selected_voice)}')
            else:
                selected_voice_info = 'Alexa - Default'
        else:
            selected_voice = None
            selected_voice_info = 'Alexa - Default'

        # call alexa_speaks
        results = alexa_remote_control.alexa_speak(ssml_text, 
                                                   device_name, 
                                                   selected_voice)
        if results:
            log_entry = (f'{device_name} : Text-to-Speech : '
                         f'{selected_voice_info}')
            self.wrapLogging(substituted_text, log_entry)
            return True
        else:
            return False 

    ###########################################################
    def typed_request(self, plugin_action, dev):
        """
        This function allows you to interact with Alexa directly 
        
        Passed to it is a text string and a device.

        TypedRequest
        """

        # announce function if debugging
        self.logger.debug("typed_request called")

        # validate Action Config for scripting
        if plugin_action.description == "plugin action":
            if not self.validatePluginExecuteAction(plugin_action, dev):
                return False

        # what to say
        the_request = plugin_action.props.get("RequestOfDevice")
        # if use wants to use an alternate name
        if dev.pluginProps["useAltName"]:
            the_device = dev.states['altDeviceName']

        else:  # otherwise use the device name
            the_device = dev.name

        # if something to be said
        if the_request:
            alexa_remote_control.ask_alexa(the_request, the_device)

    ###########################################################
    def pass_device_arg(self, plugin_action, dev):
        """
        This function also you to interact with Alexa on your device, 
        
        Passed to it is a text string and a device.

        PassDeviceArg
        """

        # announce function if debugging
        self.logger.debug("pass_device_arg called")

        # validate Action Config for scripting
        if plugin_action.description == "plugin action":
            if not self.validatePluginExecuteAction(plugin_action, dev):
                return False

        # if user wants to use an alternate name
        if dev.pluginProps["useAltName"]:
            device_name = dev.states['altDeviceName']
        else:  # otherwise use the device name
            device_name = dev.name

        # what to say
        the_arguments = plugin_action.props.get("arguments")

        # if something to be said
        if the_arguments:
            alexa_remote_control.pass_cmd_line_args(the_arguments, device_name)

    ###########################################################
    def pass_cmd_line_args(self, plugin_action, dev):
        """
        This function also you to interact with Alexa on your device, 
        
        Passed to it is a text string and a device.

        passArgs
        """

        # announce function if debugging
        self.logger.debug("pass_cmd_line_args called")

        # validate Action Config for scripting
        if plugin_action.description == "plugin action":
            if not self.validatePluginExecuteAction(plugin_action, dev):
                return False

        # what to say
        the_arguments = plugin_action.props.get("arguments")

        # if something to be said
        if the_arguments:
            alexa_remote_control.pass_cmd_line_args(the_arguments)

    ###########################################
    # Menu callbacks defined in MenuItems.xml #
    ###########################################
    def toggleDebugging(self):

        # announce function if debugging
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

        questions = valuesDict.get("questions")
        for key in questions:

            try:
                action = self.unanswered[key]['plugin_action']
                question = action.get('QuestionToAsk')
                which_device = action['whichDevice']

                # if voice monkey device exists
                dev = indigo.devices.get(int(which_device))
                if dev:
                    device_name = dev.name

                    # get the key in the device right now
                    last_question_epoch = dev.states['LastQuestionEpoch'] 

                    # if the question was just asked
                    if last_question_epoch == key:
                        # clear the device state 
                        dev.updateStatesOnServer([
                            {'key': 'LastQuestionEpoch', 'value': ''}, 
                        ])
                    # delete the question
                    del self.unanswered[key]
                    log_entry = (f"'{device_name}' pending question cancelled")
                    text = (f"{question}") 
                    self.wrapLogging(text, log_entry)

                else:  # device not found
                    
                    self.logger.error(
                      'The configured device with the ID '
                      f'"{which_device}", no longer exists. '
                       )

            except KeyError:
                self.logger.error(
                  f'The question key "{key}", no longer exists. ')

    ###########################################
    def speech_test(self, valuesDict, typeId):
        """
        This function tests a users configuration of a device 
        to convert text to speech

        """

        # indicate at WARN level that button was pressed
        self.logger.warn("'Speech Test' Button Pressed")

        # check for a device being selected
        device_id = valuesDict['whichDevice']
        if device_id:

            # create a device variable to work with
            dev = indigo.devices[int(device_id)]
            if self.plugin_prefs.get("forTextToSpeech"):
                api_used = "Alexa Remote Control"
            else:
                api_used = 'the Voice Monkey API'
            self.confirm_test(api_used, dev)

    ##########################################
    def yes_no_test(self, valuesDict, typeId):
        """
        This function tests the users configuration of a device 
        to ask and respond to yes or no questions

        """

        # indicate at WARN level that button was pressed
        self.logger.warn("'Yes/No Test' Button Pressed")

        # check for a device being selected
        device_id = valuesDict['whichDevice']
        if device_id:

            # create a device variable to work with
            dev = indigo.devices[int(device_id)]

            # get values for Voice Monkey 
            monkey_id = dev.states["monkeyId"]
            yes_preset_id = dev.states["responseYesPresetId"]
            no_preset_id = dev.states["responseNoPresetId"]

            # what to ask
            question_to_ask = "Are you able to hear me clearly?"

            # remove newline characters
            modified_text = (question_to_ask
                             .replace('\u2028', "")
                             .replace('\n', ""))

            # perform Indigo variable substitution 
            substituted_text = self.substitute(modified_text)

            # replace "&" with "&amp;" for SSML compatibility
            ssml_text = substituted_text.replace("&", "&amp;")

            # encoding query string
            encoded_text = quote(ssml_text)

            # pick random action groups..just for validation
            action_groups = indigo.actionGroups
            execute_when_yes = random.choice(action_groups.keys())
            execute_when_no = random.choice(action_groups.keys())

            ask_yes_no = actionDict('ask a yes/no question', 
                                    'YesNoQuestion',
                                    {
                                     'whichDevice': device_id,
                                     "QuestionToAsk": substituted_text,
                                     'executeWhenYes': execute_when_yes,
                                     'executeWhenNo': execute_when_no,
                                     })

            # validate plugin_action, in case I missed something
            if not self.validatePluginExecuteAction(ask_yes_no, dev):
                return False

            # update the device states
            dev.updateStatesOnServer([
                {'key': 'LastQuestionEpoch', 'value': 'Testing'}, 
            ])

            # build payload for Voice Monkey
            payload = {
                       "monkey_name": "-".join(monkey_id.lower().split()),
                       "ask_this": encoded_text,
                       "yes_preset": yes_preset_id,
                       "no_preset": no_preset_id
                      }

            # build API GET request
            query = (
                   '&monkey={monkey_name}'
                   '&announcement={ask_this}'
                   '&prompt-yes-preset={yes_preset}'
                   '&prompt-no-preset={no_preset}'
                   )

            # ensure debugging is on during this call to make_request
            debug_temp = self.debug
            self.debug = True

            if self.make_request(query, payload):

                self.logger.warn(
                    f'Device Test: ({dev.name} "{question_to_ask}"')

            else:
                self.logger.error("That did not go so well.")

            # set the debug state back to whatever it was
            self.debug = debug_temp

    ################################
    def confirm_test(self, answer, dev):

        # what to say 
        if answer in ['Yes', 'No']:
            question = 'Are you able to hear me clearly?'
            text_to_speak = (
                    f"If you responded '{answer}' to the question, "
                    f"'{question}' asked by {dev.name}, congrats, "
                    "the test was successful. ")
        else:
            text_to_speak = (
                 f"If you can hear this, your device, {dev.name}, "
                 f"was able to generate speech using {answer}. "
                 "Congrats!")

        action = actionDict('text to speech', 
                            'TextToSpeech',
                            {"TextToSpeech": text_to_speak})

        # ensure debugging is on during this call to make_request
        debug_temp = self.debug
        self.debug = True

        # validate Action Config for scripting
        if not self.validatePluginExecuteAction(action, dev):
            return False

        # call with predefine tone
        self.text_to_speech(action, dev)

        # set the debug state back to whatever it was
        self.debug = debug_temp                 

    ################################
    def show_pending_questions(self):

        num_unanswered = len(self.unanswered)
        if num_unanswered == 0:
            self.logger.info("There are no pending Yes/No Questions")
            return

        for key, value in self.unanswered.items():
            tracking = value['tracking']
            action = value['plugin_action']
            the_count = tracking['count']
            time_stamp = tracking['timestamp']
            cycles = int(action.get('cycles', 0))
            seconds = int(action.get('seconds', 0))
            question = action.get('QuestionToAsk')
            which_device = action.get('whichDevice')
            delayed = tracking.get('delayed', False)
            repeats = action.get('RepeatQuestion', False)

            if repeats and the_count < int(cycles):

                one_or_more = 'cycle' if the_count == 1 else 'cycles'
                repeat_msg = (
                    "has a repeating Yes/No Question with "
                    f"{cycles - the_count} {one_or_more} left")

                if delayed:
                    time_string = (
                        "that is 'Delayed'")
                else:

                    event_time = datetime.fromtimestamp(
                                    time_stamp) + timedelta(seconds=seconds)
                    time_diff = event_time - datetime.now()

                    m, s = divmod(time_diff.seconds, 60)
                    if time_diff.days == 0:
                        if m == 0:
                            time_string = f"due in {s} seconds"
                        else:
                            time_string = f"due in {m} minutes, {s} seconds"
                    else:
                        time_string = (
                            f"due in {time_diff.days} days, "
                            f"{m} minutes, {s} seconds")

                dev = indigo.devices.get(int(which_device))

                if dev:

                    # remove newline characters
                    ask = (question
                           .replace('\u2028', "")
                           .replace('\n', ""))

                    substituted_text = self.substitute(ask)
                    log_entry = (f'{dev.name} {repeat_msg} {time_string}')

                    indigo.server.log(log_entry)
                    indigo.server.log(f'\t"{substituted_text}"')

                else:
                    self.logger.error(
                        'The configured device with the ID '
                        f'"{which_device}", no longer exists. The '
                        'unanswered question will be removed from the list.'
                        )                        

            else:
                self.logger.info("There are no pending Yes/No Questions")
                return

    ###############################################
    # Validation of Devices, Actions, Menus, etc. #
    ###############################################

    #####################
    # Device Validation #
    #####################
    def validateDeviceConfigUi(self, valuesDict, typeId, devId): 
        self.logger.debug("Validating device config")

        # create a Dict for errors
        errorsDict = indigo.Dict()
    
        def validate_monkey_id(valuesDict):
            # if no monkey ID given
            monkey_id = valuesDict.get("monkey_id", "")
            useAltName = valuesDict.get("useAltName", False)
            if len(monkey_id) < 1:
                if not useAltName:
                    errorsDict["monkey_id"] = (
                                   "Invalid Monkey ID entered"
                                           )
                    self.logger.error(errorsDict["monkey_id"])
                    errorsDict["showAlertText"] = (
                                   "What you should enter here, is the "
                                   "name of the device you configured on "
                                   "the Voice Monkey site. Click ? for "
                                   "https://app.voicemonkey.io"
                        )

        def validate_device_name(valuesDict, devId):

            dev = indigo.devices[int(devId)]
            useAltName = valuesDict.get("useAltName", False)
            useCustomName = valuesDict.get("useCustomName", False)
            AltDeviceName = valuesDict.get("AltDeviceName", "")
            discoveredDevice = valuesDict.get("discoveredDevice", "")

            if useAltName:
                if discoveredDevice == 'Default' or discoveredDevice == '':
                    valuesDict["AltDeviceName"] = AltDeviceName
                elif len(discoveredDevice) > 1:
                    valuesDict["AltDeviceName"] = discoveredDevice
                else:
                    valuesDict["AltDeviceName"] = dev.name

                if discoveredDevice == "Default" or discoveredDevice == "":
                    if len(AltDeviceName) < 1:
                        errorsDict["AltDeviceName"] = (
                            "An invalid device name was entered."
                        )
                        self.logger.error(errorsDict["AltDeviceName"])

                        errorsDict["showAlertText"] = (
                            "You have to either select a discovered "
                            "device, or type in a custom device name."
                            )
                    elif not useCustomName:
                        errorsDict["useAltName"] = (
                            "Invalid device name settings configuration."
                        )
                        errorsDict["showAlertText"] = (
                            "No was name selected. Please uncheck "
                            "'Use an Alternate device'"
                            )
                # if Use Custom Name check box ticked
                elif useCustomName:
                    if len(AltDeviceName) > 1:
                        errorsDict["discoveredDevice"] = (
                            "An invalid device name was entered."
                        )
                        errorsDict["AltDeviceName"] = (
                            "An invalid device name was entered."
                        )
                        self.logger.error(errorsDict["AltDeviceName"])
                        errorsDict["showAlertText"] = (
                            "You have to either select a discovered "
                            "device, or type in a custom device name."
                        )

            else:
                valuesDict["AltDeviceName"] = ""

        def validate_preset_ids(valuesDict):
            for preset in ['yes_preset_id', 'no_preset_id']:
                err_msg = (
                     "Please enter either numerical digits (1, 2, 3, etc.)"
                     " or the written words representing the numbers "
                     "(one, two, three, etc.). The correct value can be "
                     "found under API -> Presets Click '?' for "
                     "https://voicemonkey.io/ "
                    )
                # leaving the fields blank is allowed
                if valuesDict[preset]:
                    if valuesDict[preset].isdigit():
                        try:
                            # if a invalid value is provide 0 or less
                            a_preset_id = int(valuesDict[preset])
                            if a_preset_id < 1:
                                raise
                        except:  # noqa
                            errorsDict[preset] = "Invalid Preset IDs"
                            self.logger.error(errorsDict[preset])
                            errorsDict["showAlertText"] = err_msg

                    else:  # not a digit
                        # if the number value was typed out (i.e. 'five')
                        if self._text2int(valuesDict[preset]):
                            # update dictionary with the integer value
                            valuesDict[preset] = self._text2int(
                                                    valuesDict[preset])
                        else:
                            errorsDict[preset] = "Invalid Preset IDs"
                            self.logger.error(errorsDict[preset])
                            errorsDict["showAlertText"] = err_msg
                else:
                    valuesDict[preset] = ''  

        # Validate based on typeId
        if typeId == "VoiceMonkeyDevice":

            validate_monkey_id(valuesDict)
            validate_preset_ids(valuesDict)
            validate_device_name(valuesDict, devId)

        # check for errors  #
        if len(errorsDict) > 0:
            return (False, valuesDict, errorsDict)
        return (True, valuesDict)
    
    #####################
    # Action Validation #
    #####################
    def validateActionConfigUi(self, valuesDict, typeId, devId):

        self.logger.debug(
            f"Validating action config for type: {typeId} for {devId}"
            )

        # setup a Indigo Dictionary to track errors
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
                    "The URL must begin with https://"
                )
                errorsDict["showAlertText"] = errorsDict["audioFileUrl"]
                self.logger.error(errorsDict["audioFileUrl"])

        def validate_play_background_audio_file(valuesDict):
            if not self.validateURL(
                 valuesDict.get("backgroundAudioFileUrl", "")):

                errorsDict["backgroundAudioFileUrl"] = (
                    "Enter a publicly accessible URL. "
                    "The URL must begin with https://"
                )
                errorsDict["showAlertText"] = errorsDict[
                                                "backgroundAudioFileUrl"]
                self.logger.error(errorsDict["backgroundAudioFileUrl"])

        def validate_trigger_routine(valuesDict):
            if len(valuesDict.get("monkey_id", "")) < 1:
                errorsDict["monkey_id"] = (
                    "The 'monkey_id' is surely at least one character long"
                )
                self.logger.error(errorsDict["monkey_id"])

                errorsDict["showAlertText"] = (
                    "This value can be found on voicemonkey.io, "
                    "under API -> Preset and is in the Monkey ID column"
                )

        def validate_typed_request(valuesDict):
            RequestOfDevice = valuesDict.get("RequestOfDevice", "")
            if not self.plugin_prefs.get("AltModuleImported"):
                errorsDict["RequestOfDevice"] = (
                    "Additional configuration is required. "
                    "This is not a capability of the Voice Monkey API."
                )
                errorsDict["showAlertText"] = errorsDict["RequestOfDevice"]
                self.logger.error(errorsDict["RequestOfDevice"])

            if len(RequestOfDevice) < 1:
                errorsDict["RequestOfDevice"] = "You have to enter something."
                self.logger.error(errorsDict["RequestOfDevice"])
                errorsDict["showAlertText"] = (
                    "Type in your request, just as you would speak it to your "
                    "Alexa device. You don't need your wake word"
                )

        def validate_alexa_routine(valuesDict):
            monkey_id = valuesDict.get("monkey_id", "")
            if not self.plugin_prefs.get("AltModuleImported"):
                errorsDict["monkey_id"] = (
                    "Additional configuration is required. "
                    "This is not a capability of the Voice Monkey API."
                )
                errorsDict["showAlertText"] = errorsDict["monkey_id"]
                self.logger.error(errorsDict["monkey_id"])

            if len(monkey_id) < 1:
                errorsDict["monkey_id"] = "You have to enter something."
                self.logger.error(errorsDict["monkey_id"])
                errorsDict["showAlertText"] = (
                    "Type in your EXACT name of your Alexa Routine, as shown "
                    "in the Alexa App."
                )

        def validate_pass_args(valuesDict):
            arguments = valuesDict.get("arguments", "")
            if not self.plugin_prefs.get("AltModuleImported"):
                errorsDict["arguments"] = (
                    "Additional configuration is required. "
                    "This is not a capability of the Voice Monkey API."
                )
                errorsDict["showAlertText"] = errorsDict["arguments"]
                self.logger.error(errorsDict["arguments"])

            if len(arguments) < 1:
                errorsDict["arguments"] = "No arguments specified."
                self.logger.error(errorsDict["arguments"])
                errorsDict["showAlertText"] = (
                    "Type in arguments that you want to send to your "
                    "Alexa device(s). Click '?' for available commands."
                )

        def validate_device(valuesDict):
            which_device = valuesDict.get("whichDevice", 0)
            if which_device:
                try:
                    smart_device = indigo.devices[int(which_device)]
                    response_preset_ids = ['responseYesPresetId', 
                                           'responseNoPresetId']
                    for preset_id in response_preset_ids:
                        if not smart_device.states.get(preset_id):
                            err_msg = (
                                "The selected device is not configured "
                                "for Yes or No questions"
                                )
                            self.logger.error(err_msg)
                            errorsDict["QuestionToAsk"] = err_msg
                            errorsDict["showAlertText"] = (
                                "You cannot ask Yes or No questions on the "
                                "selected device because it is not configured "
                                "to respond. "
                                "To change the device settings, find the "
                                "device in the device table, double-click it "
                                "(or select it an click the Edit… button) and "
                                "then choose 'Edit Device Settings'. "
                                "Once there, enter the appropriate values for "
                                "the Yes and No Preset IDs."
                                )
                            break
                except KeyError:  # device doesnt exist
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

            execute_when_no = valuesDict.get('executeWhenNo', False)
            execute_when_yes = valuesDict.get('executeWhenYes', False)

            # handle if use selected '- select an action group -'
            if execute_when_no == '0': 
                execute_when_no = False
            if execute_when_yes == '0':
                execute_when_yes = False

            no_response_group = valuesDict.get("noResponseActionGroup", 0)
            execute_no_response = bool(valuesDict.get("executeNoResponse", 
                                                      False))

            if not execute_when_yes and not execute_when_no:
                err_msg = ("You have to select a Action Group to Execute for "
                           "at least one response, Yes or No")
                self.logger.error(err_msg)
                errorsDict['executeWhenYes'] = err_msg
                errorsDict['executeWhenNo'] = err_msg
                errorsDict["showAlertText"] = err_msg
            else:
                for yes_or_no in ['executeWhenYes', 'executeWhenNo']:
                    action_group = valuesDict.get(yes_or_no, False)
                    if (action_group 
                       and not self.validate_action_group_id(action_group)):

                        err_msg = ("A valid Action Group is needed for either "
                                   "the Yes or No response.")
                        self.logger.error(err_msg)
                        errorsDict[yes_or_no] = err_msg
                        errorsDict["showAlertText"] = err_msg

            if execute_no_response:
                if no_response_group:
                    if no_response_group == '0':
                        no_response_group = None
                        valuesDict["noResponseActionGroup"] = no_response_group
                    elif self.validate_action_group_id(no_response_group):
                        valuesDict["noResponseActionGroup"] = int(no_response_group)  # noqa
                    else:
                        err_msg = (
                            "You must select a valid Action Group "
                            "to be executed, if the option is ticked."
                        )
                        errorsDict["noResponseActionGroup"] = err_msg
                        errorsDict["showAlertText"] = err_msg
                        self.logger.error(err_msg)
                else:
                    err_msg = (
                        "You must select a valid Action Group "
                        "to be executed, if the option is ticked."
                    )
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
                    errorsDict["showAlertText"] = (cycles_error)

                if seconds < self.min_delay:
                    self.logger.error(seconds_error)
                    errorsDict["seconds"] = seconds_error
                    errorsDict["showAlertText"] = (seconds_error)

        def validate_yes_no_question(valuesDict):

            result = self.isPluginRunning('alexa')
            if not result["plugin_enabled"]:
                err_msg = 'The Indigo Alexa plugin is not enabled.'
                errorsDict["QuestionToAsk"] = (err_msg)
                self.logger.error(err_msg)
                errorsDict["showAlertText"] = (
                    "To implement 'Ask a Yes/No Question', you have "
                    "to Enable the Indigo Alexa plugin."
                    )

            question_to_ask = valuesDict.get("QuestionToAsk", "")
            if not question_to_ask:
                err_msg = (
                    "The question you want to ask has an invalid format")
                self.logger.error(err_msg)
                errorsDict["QuestionToAsk"] = (err_msg)
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
                    "You must type in the EXACT text of the Yes/No Question, "
                    "in order to cancel it. TIP: Use copy & paste.")
                self.logger.error(errorsDict["question_to_cancel"])
                errorsDict["showAlertText"] = errorsDict["question_to_cancel"]

        def validate_announcements(valuesDict):

            result = self.isPluginRunning('announcements')
            if not result["plugin_enabled"]:
                err_msg = 'The Announcements Plugin is not enabled. '
                errorsDict["Announcements"] = (err_msg)
                self.logger.error(err_msg)
                errorsDict["showAlertText"] = (
                    "To use 'Speak Announcements', you have "
                    "to Enable the Announcements plugin."
                    )

            # get Announcement Source and Item to Speak
            source_id = valuesDict["theAnnouncement"]
            announcementToSpeak = valuesDict["announcementToSpeak"]

            # this will be a digit, if something is entered
            if not source_id.isdigit():
                err_msg = (
                           'Please select a Source.'
                           )
                errorsDict["theAnnouncement"] = (err_msg)
                self.logger.error(err_msg)
                errorsDict["showAlertText"] = (err_msg)

            # validate Announcement Devices
            elif indigo.devices[int(source_id)].model == "Announcements Device":  # noqa

                # get all Announcements Devices
                plugin = indigo.server.getPlugin(self.announcements_pid)
                result = plugin.executeAction("exportAnnouncements")
                all_announcements = json.loads(result)

                # get selected the announcement
                announcements = all_announcements[source_id]

                # modify the name, then search for the matching announcement
                modified_name = announcementToSpeak.replace("_", " ")
                matching_items = [v for k, v in announcements.items() 
                                  if v['Name'] == modified_name]
                announcement_message = (matching_items[0]['Announcement'] 
                                        if matching_items else None)

                # process the announcement message if found
                if announcement_message is None:
                    err_msg = ('Announcement not found')
                    errorsDict["announcementToSpeak"] = (err_msg)
                    self.logger.error(err_msg)
                    errorsDict["showAlertText"] = (err_msg)

                elif re.search(r'\[\[.*?\]\]', announcement_message):
                    err_msg = (
                               'This Plugin is unable to interpret the '
                               'embedded speech commands in the selected '
                               'announcement.')
                    errorsDict["announcementToSpeak"] = (err_msg)
                    self.logger.error(err_msg)
                    errorsDict["showAlertText"] = (err_msg)

            else:  # validate "Salutations Device"

                # determine if something was selected
                if len(announcementToSpeak) < 1:
                    err_msg = (
                               'Please select an Item to Speak.'
                               )
                    errorsDict["announcementToSpeak"] = (err_msg)
                    self.logger.error(err_msg)
                    errorsDict["showAlertText"] = (err_msg)

        # Validate based on typeId
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
            self.logger.debug(f'unaccounted for: {typeId}')

        # where there any errors?
        if len(errorsDict) > 0:
            return (False, valuesDict, errorsDict)
        return (True, valuesDict)        

    ###########################
    # PluginConfig Validation #
    ###########################
    def validatePrefsConfigUi(self, valuesDict):

        # announce function if debugging
        self.logger.debug("validatePrefsConfigUi called")

        errorsDict = indigo.Dict()

        # Validate tokens preferences
        def validate_tokens_pref(valuesDict):

            # validate Access and Secret Tokens
            access_token = valuesDict.get("accessToken", '')
            secret_token = valuesDict.get("secretToken", '')

            # if either access token not enter, warn the user but allow it
            if not (len(access_token) >= 1 and len(secret_token) >= 1):
                # if using the alexa_remote_control_module
                if valuesDict.get('useAlexaRemoteControl', False):
                    self.logger.warn(
                        'To use any function that requires the Voice Monkey '
                        "API, such as audio playback "
                        )
                    self.logger.warn(
                        "or verbally prompted 'Yes or No' questions, "
                        "API Tokens are required."
                                     )
                    self.logger.warn(
                        "The imported 'alexa_remote_control' module can "
                        " handle text-to-speech and sound playback, if "
                        "it is set up and configured correctly."
                                     )

                else:  # if not using the alexa_remote_control_module
                    errorMsg = (
                        'Voice Monkey API Tokens are not configured correctly')
                    errorsDict["accessToken"] = errorMsg
                    errorsDict["secretToken"] = errorMsg
                    errorsDict["showAlertText"] = (
                            'To use the Voice Monkey API, you must '
                            'enter both your Secret and Access Tokens')

        # Validate announcement plugin preferences
        def validate_announcements_pref(valuesDict):

            enable_subscription = valuesDict.get('enableSubscription', False)
            announcing_device = valuesDict.get('announcingDevice', False)
            change_voice = valuesDict.get('ChangeVoice', False)
            selected_voice = valuesDict.get('selectedVoice', False)

            # if subscription is enabled
            if enable_subscription:

                # check to see if the Announcements Plugin is running
                result = self.isPluginRunning('announcements')
                if not result["plugin_enabled"]:
                    errorMsg = ('The Announcements Plugin is not enabled. '
                                "It is required to use Variable Subscription.")
                    errorsDict["enableSubscription"] = errorMsg
                    errorsDict["showAlertText"] = (errorMsg)

                # error if a device is not selected
                elif not announcing_device:
                    errorMsg = ("Please select a device to speak when you "
                                "the 'Speak Announcement' button within "
                                "the Announcements plugin is pressed")
                    errorsDict["announcingDevice"] = errorMsg
                    errorsDict["showAlertText"] = (errorMsg)
                else:
                    self.announcing_device = announcing_device

                # if a different voice is not wanted
                if not change_voice:
                    self.selected_voice = None
                elif selected_voice and selected_voice not in voices:
                    errorsDict["selectedVoice"] = (
                        f"The voice '{selected_voice}' is not recognized")
                    errorsDict["showAlertText"] = (errorsDict["selectedVoice"])
                elif not selected_voice:
                    errorsDict["selectedVoice"] = (
                        "Please select a voice or uncheck 'Change the Voice?'")
                    errorsDict["showAlertText"] = (errorsDict["selectedVoice"])
                else:
                    self.selected_voice = selected_voice
                    self.change_voice = change_voice

            else:  # variable subscription is disabled

                self.announcing_device = False
                self.selected_voice = None
                self.change_voice = False
                valuesDict['ChangeVoice'] = False

        # Validate yes/no question timing preferences
        def validate_yesno_timing_pref(valuesDict):

            # Validate Yes/No timing
            adjust_timing = valuesDict.get('AdjustTiming', False)
            if adjust_timing:
                try:
                    max_time_to_wait = int(valuesDict.get('maxTimeToWait'))
                    if max_time_to_wait < 5:
                        raise ValueError("maxTimeToWait must be at least 5.")
                except (ValueError, TypeError) as e:
                    self.logger.debug(str(e))
                    errorMsg = ('Invalid entry, a positive number greater '
                                'than 5 was not entered')
                    errorsDict["maxTimeToWait"] = errorMsg
                    errorsDict["showAlertText"] = (
                        'The maximum number of seconds to wait for a '
                        'Yes or No response must be a positive number '
                        'greater than 5.')
                else:
                    self.max_wait = max_time_to_wait

                try:
                    min_yes_no_delay = int(valuesDict.get('minYesNoDelay'))
                    if min_yes_no_delay < 5:
                        raise ValueError("minYesNoDelay must be at least 5.")
                except (ValueError, TypeError) as e:
                    self.logger.debug(str(e))
                    errorMsg = ('Invalid entry, a positive number greater '
                                'than 5 was not entered')
                    errorsDict["minYesNoDelay"] = errorMsg
                    if "showAlertText" not in errorsDict:
                        errorsDict["showAlertText"] = (
                            'The minimum number of seconds that must elapse '
                            'before a question can be repeated, must be a '
                            'positive number greater than 5')
                    else:
                        errorsDict["showAlertText"] += (
                            ' Also, the minimum number of seconds for '
                            'minYesNoDelay must be greater than 5.')
                else:
                    self.min_delay = min_yes_no_delay

                try:
                    sleep_time = int(valuesDict.get('sleepTime'))
                    if sleep_time < 1:
                        raise ValueError("sleepTime cannot be less than 1.")
                except (ValueError, TypeError) as e:
                    self.logger.debug(str(e))
                    errorMsg = 'Invalid entry, value cannot be less than 1.'
                    errorsDict["sleepTime"] = errorMsg
                    if "showAlertText" not in errorsDict:
                        errorsDict["showAlertText"] = (
                            'Specify the number of seconds to pause between '
                            'iterations of the runConcurrentThread() function '
                            'by entering a value in the text field. '
                            'The default value is 5 seconds.')
                    else:
                        errorsDict["showAlertText"] += (
                            ' Also, the sleepTime must be a positive number '
                            'and cannot be less than 1.')
                else:
                    self.sleep_time = sleep_time

            else:  # change them back to defaults if unchecked
                self.min_delay = 35
                self.max_wait = 30
                self.sleep_time = 5
                valuesDict['minYesNoDelay'] = 35
                valuesDict['maxTimeToWait'] = 30
                valuesDict['sleepTime'] = 5

        # Validate alexa remote control preferences
        def validate_alexa_remote_control_pref(valuesDict):

            use_alexa_remote = valuesDict.get('useAlexaRemoteControl', False)

            if use_alexa_remote:
                errorMsg = (
                            "Additional configuration is required "
                            "before this selection is allowed. See "
                            "the documenation for more information."
                            )
                if not self.plugin_prefs.get("AltModuleImported"):
                    # don't allow this configuration
                    errorsDict["showAlertText"] = errorMsg
                    errorsDict["use_alexa_remote"] = errorMsg
            else:  # not using alexa remote control
                valuesDict['forTextToSpeech'] = False
                valuesDict['forPlayingSounds'] = False

        # configure debugging
        def configure_debug_pref(valuesDict):
            
            show_debug_messages = valuesDict.get("showDebugInfo", False)
            self.debug = show_debug_messages
            if show_debug_messages:
                self.logger.info("debug logging is on")
            else:
                self.logger.info("debug logging is off")

        # Validate logging preferences
        def validate_logging_pref(valuesDict):

            # Validate and convert max_combined_length
            try:
                self.max_combined_length = int(valuesDict.get(
                                               "maxCombinedLength", 150))
                if self.max_combined_length < 25:
                    raise ValueError("maxCombinedLength must be at least 25.")
            except (ValueError, TypeError) as e:
                self.logger.debug(str(e))
                errorMsg = ('Invalid entry, a positive number greater than 25 '
                            'was not entered for the character length.')
                errorsDict["maxCombinedLength"] = errorMsg
                errorsDict["showAlertText"] = (
                    'The minimum character value for maxCombinedLength is 25. '
                    'The default was 150.')

            try:
                self.max_text_length = int(valuesDict.get(
                                           "maxTextLength", 150))
                if self.max_text_length < 25:
                    raise ValueError("maxTextLength must be at least 25.")
            except (ValueError, TypeError) as e:
                self.logger.debug(str(e))
                errorMsg = ('Invalid entry, a positive number greater than 25 '
                            'was not entered for the character length.')
                errorsDict["maxTextLength"] = errorMsg
                if "showAlertText" not in errorsDict:
                    errorsDict["showAlertText"] = (
                        'The minimum character value for maxTextLength is 25. '
                        'The default was 150.')
                else:
                    errorsDict["showAlertText"] += (
                        ' Also, the minimum character value for maxTextLength '
                        'is 25. The default was 150.')

        #########################
        #  Validate Preferences #
        #########################

        # Validate tokens preferences
        validate_tokens_pref(valuesDict) 

        # Validate announcement plugin preferences
        validate_announcements_pref(valuesDict)

        # Validate yes/no question timing preferences
        validate_yesno_timing_pref(valuesDict)

        # Validate alexa remote control preferences
        validate_alexa_remote_control_pref(valuesDict)

        # configure debugging
        configure_debug_pref(valuesDict)

        # Validate logging preferences
        validate_logging_pref(valuesDict)

        # where there any errors?
        if len(errorsDict) > 0:
            return (False, valuesDict, errorsDict)
        return (True, valuesDict)

    ####################
    # Config UI Closed #
    ####################
    def closedPrefsConfigUi(self, valuesDict, userCancelled):

        self.logger.debug("closedPrefsConfigUi called")

        # restart the plugin if the user, enabled or disabled subscription
        if self.subscription_enabled != valuesDict.get('enableSubscription', 
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
        """
        This function pass arguments on to validateActionConfigUi.

        It is intended to be used to validate arguments passed
        to the plugin thru scripting. 

        It returns True if everything validates and False if not
        """

        # announce function if debugging
        self.logger.debug("validatePluginExecuteAction called")

        if isinstance(dev, indigo.RelayDevice):
            device_id = dev.id
        else:
            device_id = dev

        return self.validateActionConfigUi(plugin_action.props, 
                                           plugin_action.pluginTypeId, 
                                           device_id)[0]

    ######################################################
    # valid the action group passed
    def validate_action_group_id(self, ag_id):

        # announce function if debugging
        self.logger.debug("validate_action_group_id called")

        # check if a valid Action Group was given, allow 0, for none
        if not ag_id:
            return True
        elif int(ag_id) == 0:
            return True
        
        try:
            if indigo.actionGroups[int(ag_id)]:
                return True 

        except ValueError:
            self.logger.error(
                f'The previously configured Action Group ID "{ag_id}"", '
                'no longer exists. Was it deleted?'
                )
            return False

    ###########################################################
    def monkey_validation(self, plugin_action, dev=None):
        """
        This function is used to validate the Voice Mnkey API can be used.
        It checks that a value for the Monkey ID will be passed and that
        both the Secret and Access Token are configured.

        The checked items would not necessarily stops operation
        of the plugin if the user is using the Alternate module 
        
        It returns True if the it can validate what was passed to it
        and False if it can not, and prints a message for the user in the log
        """

        # announce function if debugging
        self.logger.debug("monkey_validation called")

        access_token = self.plugin_prefs.get("accessToken")
        secret_token = self.plugin_prefs.get("secretToken")

        # check if a useable Monkey Id values is configured
        if isinstance(dev,  indigo.RelayDevice):
            props = dev.pluginProps
            monkey_id = props.get("monkey_id", None)
        else:
            monkey_id = plugin_action.props.get('monkey_id') 
        
        # if a Yes/No Question action, check if the Alexa App is running
        if plugin_action.pluginTypeId == "YesNoQuestion":
            result = self.isPluginRunning('alexa')
        else:
            result = None

        # define items to check with error messages if check fails
        errors = {
            "accessToken": "To use the Monkey Voice API, you must configure "
                           "an Access Token.",
            "secretToken": "To use the Monkey Voice API, you must configure "
                           "a Secret Token.",
            "monkey_id": "The Voice Monkey functions are not fully configured "
                         "for this device.",
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
        return not bool(error_fields)  # returns True if no errors

    ################################
    # Functions handling Questions #
    ################################
    def find_props(self, find_value):
        for key, value in self.unanswered.items():
            if value.get('plugin_action') == find_value:
                return key
        return None

    ################################
    def questionList(self, filter="", valuesDict=None, typeId="", targetId=0):
        '''
        This is a dynamic list for an Action.xml
        '''
        values = []
        for key in self.unanswered.keys():
            which_device = self.unanswered[key]['plugin_action']['whichDevice']
            dev = indigo.devices[int(which_device)]
            question = self.unanswered[key]['plugin_action']['QuestionToAsk']

            # remove newline characters
            question_to_ask = (question
                               .replace('\u2028', "")
                               .replace('\n', ""))

            value = (key, f'{dev.name} - {question_to_ask}')
            values.append(value)
        return values

    #################################################
    # Functions Related to the Announcemetns Plugin #
    #################################################
    def refresh_fields(self, plugin_action, dev, something):
        """ 
        Dummy callback to force dynamic control refreshes
        The refresh_fields() method is a dummy callback used solely 
        to fire other actions that require a callback be run. 
        It performs no other function.
        :param str fltr:
        :param str type_id:
        :param int target_id:
        """
        self.logger.debug("refresh_fields")

    def announcement_speak_action(self, plugin_action, dev):
        """

        """
        self.logger.debug("announcement_speak_action")

        # check to see if the Announcements Plugin is running
        result = self.isPluginRunning('announcements')
        if not result["plugin_enabled"]:
            err_msg = ('The Announcements Plugin is not enabled. '
                       "The 'Speak Announcements' Device Action requires it.")
            self.logger.error(err_msg)
            return False

        # get Announcement Source and Item to Speak
        source_id = int(plugin_action.props['theAnnouncement'])
        announcement_name = plugin_action.props["announcementToSpeak"]

        # what voice to use
        selected_voice = plugin_action.props.get( 
                                "selectedAnnouncementVoice", False)
        change_voice = plugin_action.props.get(
                                "ChangeAnnouncementVoice", True)

        # if device does not exist
        if indigo.devices.get(source_id) is None:
            err_msg = ('Announcements device not found. Please edit the '
                       'Action Group and select another device.')
            self.logger.error(err_msg)
            return False

        elif not indigo.devices[source_id].enabled:
            err_msg = ('The selected Announcements is not enabled. ')
            self.logger.warn(err_msg)
            return False

        # if an Announcement Devices
        elif indigo.devices[source_id].model == "Announcements Device":

            # get all Announcements devices
            plugin = indigo.server.getPlugin(self.announcements_pid)
            result = plugin.executeAction("exportAnnouncements")
            exported_announcements = json.loads(result)

            # get selected the announcement
            announcements = exported_announcements[str(source_id)]

            # modify the name, then search for the matching announcement
            matching_name = announcement_name.replace("_", " ")
            matching_items = [v for k, v in announcements.items()
                              if v['Name'] == matching_name]
            announcement_message = (matching_items[0]['Announcement']
                                    if matching_items else None)

            # process the announcement message if found
            if announcement_message is not None:

                if ('[[' in announcement_message and
                        ']]' in announcement_message):
                    err_msg = ("This plugin cannot interpret speech commands "
                               "in the selected announcement. Please update "
                               "the announcement with Speech Synthesis "
                               "Markup Language (SSML) commands."
                               )
                    self.logger.error(err_msg)
                    return False

                elif ('<<' in announcement_message and
                      '>>' in announcement_message):

                    # refresh the Announcement, then use its
                    plugin.executeAction(
                        "refreshAnnouncementData", source_id,
                        {'announcementToRefresh': announcement_name,
                         'announcementDeviceToRefresh': source_id})

                    # pause to allow device state to update
                    self.sleep(0.5)

                    # get device state
                    the_device = indigo.devices[source_id]
                    text_to_speak = the_device.states[announcement_name]

                else:  # no modifiers used
                    text_to_speak = announcement_message

                # prepare and then speak announcement
                action = actionDict('text to speech', 'TextToSpeech',
                                    {"selectedVoice": selected_voice,
                                     "ChangeVoice": change_voice,
                                     "TextToSpeech": text_to_speak})
                self.text_to_speech(action, dev)

            else:  # announcment not found
                self.logger.warn('The configured Announcement was not found')

        else:  # "Salutations Device" detected

            # use the device state for the text to speak
            text_to_speak = (indigo.devices[source_id].
                             states[announcement_name])
            action = actionDict('text to speech', 'TextToSpeech',
                                {"selectedVoice": selected_voice,
                                 "ChangeVoice": change_voice,
                                 "TextToSpeech": text_to_speak})
            self.text_to_speech(action, dev)

    def deviceList(self, dev_filter=None):
        """
        Returns a list of tuples containing Indigo devices 
        for use in config dialogs (etc.)
        :param str dev_filter:
        :return: [(ID, "Name"), (ID, "Name")]
        """
        devices_list = [('None', 'None')]
        devices_list.extend((dev.id, dev.name) 
                            for dev in indigo.devices.iter(dev_filter))
        return devices_list

    def announcement_devices(self, filter="", valuesDict=None, typeId="", targetId=0):  # noqa
    # def announcement_devices(self, valuesDict, dev):  # noqa
        """
        Returns a list of tuples containing Indigo devices 
        for use in config dialogs (etc.)
        :param str dev_filter:
        :return: [(ID, "Name"), (ID, "Name")]
        """
        return self.deviceList(self.announcements_pid)

    @staticmethod
    def generator_announcement_list(filter="", values_dict=None, type_id="", target_id=0):  # noqa
        """
        Generate a list of states for Indigo controls
        Returns a list of states for selected plugin device.
        :param str fltr:
        :param indigo.Dict values_dict:
        :param str type_id:
        :param int target_id:
        :return list result:
        """
        try:
            announcement_id = int(values_dict['theAnnouncement'])
            if announcement_id in indigo.devices:
                result = [
                    (state, state.replace("_", " "))
                    for state in indigo.devices[announcement_id].states
                    if 'onOffState' not in state
                ]
            else:
                result = [('value', 'Value')]
        except KeyError:
            result = [('None', 'None')]
        except ValueError:
            result = [('None', 'None')]

        return result

    ###########################
    # Miscellaneous Functions #
    ###########################
    def make_request(self, query, payload):
        """

        Sends a GET request to the VoiceMonkey API using the 
        access token and secret token stored in the plugin preferences. 
        Returns the API response.

        Args:
            query (str): The partial URL to send the request to.
            payload (dict): A dictionary of parameters to include in 
            the request.

        Returns:
            requests.Response: The API response.

        Raises:
            requests.exceptions.RequestException: If an error occurs 
            while making the request.

        """
        # announce function if debugging
        self.logger.debug("make_request called")

        url = ('https://api.voicemonkey.io/trigger?'
               f'access_token={self.plugin_prefs.get("accessToken")}'
               f'&secret_token={self.plugin_prefs.get("secretToken")}'
               f'{query}')

        # show the full url without the keys
        self.logger.debug(self.sanitizeOutput(url.format(**payload)))

        try:

            response = requests.get(f'{url.format(**payload)}', timeout=5)
            self.logger.debug(f"response: {response}")
            response.raise_for_status()
            # Code below here will only run if the request is successful
            self.logger.debug(
                "Your request queued successfully. "
                "This doesn't guarantee the Monkey will trigger."
                )
            return True

        except requests.exceptions.RequestException as e:
            # removed Tokens from logged messages
            self.logger.error(self.sanitizeOutput(f"{e}"))
            return False

    def sanitizeOutput(self, string):
        """
        This function removes the access and secret tokens in the input string
        and returns the string

        """
        # Replace access token with 'ACCESS_TOKEN'
        string = re.sub(re.escape(
            self.plugin_prefs.get("accessToken")), 'ACCESS_TOKEN', string)

        # Replace secret token with 'SECRET_TOKEN'
        string = re.sub(re.escape(
            self.plugin_prefs.get("secretToken")), 'SECRET_TOKEN', string)

        return string

    def wrapLogging(self, substituted_text, log_entry):  

        # combine the output lines
        combined_text = f'{log_entry} : "{substituted_text}"'

        if len(combined_text) > self.max_combined_length:
            wrapped_text = textwrap.wrap(substituted_text, 
                                         width=self.max_text_length)
            indigo.server.log(f'{log_entry}')
            for line in wrapped_text:
                indigo.server.log(f'"{line}"')

        else:
            indigo.server.log(f'{combined_text}')  
  
    def myListGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):  # noqa
        """

        """
        if self.plugin_prefs.get("AltModuleImported", False):
            myArray = alexa_remote_control.list_available_devices()
            return myArray
        return [('Default', '')]

    def myActionGroupList(self, filter="", valuesDict=None, typeId="", targetId=0):  # noqa
        """
        This function was used by Question_Modifier, which was removed.
        It's still a good code example...leaving it for a while.


        """
        pluginId = 'com.anyone.indigoplugin.voice-monkey'
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
        """
        Dynamic list of the different voices within alexa_constants.py

        """
        voice_list = []
        for name, description in voices.items():
            voice_list.append((name, description))
        return voice_list

    def soundsList(self, filter="", valuesDict=None, typeId="", targetId=0):  # noqa
        """
        Dynamic list of the different sounds within alexa_constants.py

        """
        sounds_list = []
        for path, name in sounds.items():
            sounds_list.append((path, name))
        return sounds_list

    def actionsWithAnExit(self, filter="", valuesDict=None, typeId="", targetId=0):  # noqa
        """
        
        Needed to provide a selection for the User after creating and saving, 
        an action, then wanting to change an Action Group value to 
        None/Nothing/Blank
        
        """
        action_group_list = [(ag.id, ag.name) for ag in indigo.actionGroups]
        sorted_list = sorted(action_group_list, key=lambda x: x[1].lower())
        sorted_list.insert(0, (0, '- select an action group -'))
        return sorted_list if sorted_list else [(0, '')]

    def find_by_action(self, ID):  
        """
        This function returns a Voice Monkey device, if found,
        based on an Action Group ID passed to it
        
        """            
        devices = []
        # make a list of all the Voice Monkey devices which are configured
        for dev in indigo.devices.iter("self"):
            devices.append(dev.id)

        # search the action groups dependent on these devices
        device_action_list = []
        for device in devices:
            data = indigo.device.getDependencies(device)
            for entry in data["actionGroups"]:
                device_action_list.append((entry["ID"], entry["Name"], device))

        for id, name, device in device_action_list:
            if id == ID:
                return device

    def isPluginRunning(self, plugin_name):

        plugin_names = {
            'alexa': 
            {'plugin_id': 'com.indigodomo.indigoplugin.alexa'},
            'announcements': 
            {'plugin_id': self.announcements_pid},
        }

        # check if the Plugin is running
        plugin_id = plugin_names[plugin_name]['plugin_id']
        plugin = indigo.server.getPlugin(plugin_id)
        plugin_enabled = plugin.isEnabled()

        return {
                "plugin_enabled": plugin_enabled
                }

    ###########################
    def validateURL(self, url):
        '''
        This function validates a URL formating and only accept https://
        '''
        regex = ("^((https)://)[-a-zA-Z0-9@:%._\\+~#?&//=]{2,256}"
                 "\\.[a-z]{2,6}\\b([-a-zA-Z0-9@:%._\\+~#?&//=]*)$")

        substituted_url = self.substitute(url)
        r = re.compile(regex)
        if (re.search(r, substituted_url)):
            return True
        else:
            return False

    ###########################
    @staticmethod
    def _text2int(textnum, numwords={}):
        """
            Convert a word string into an integer
            
            Parameters:
            textnum (str): The word string that represents a number
            numwords (dict): A dictionary of word-number mappings. 
            Default is an empty dictionary.
            
            Returns:
            int: The integer representation of the input word string
            
            Example:
            text2int("twenty-seven") => 27
            """

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
        # remove "-" so twenty-seven works
        cleaned_textnum = textnum.replace("-", " ")
        for word in cleaned_textnum.split():
            if word not in numwords:
                # raise Exception("Illegal word: " + word)
                return

            scale, increment = numwords[word]
            current = current * scale + increment
            if scale > 100:
                result += current
                current = 0
        return result + current
