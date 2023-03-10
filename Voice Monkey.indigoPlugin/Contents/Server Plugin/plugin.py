#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################

import re
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
        self.max_text_length = plugin_prefs.get("maxTextLength", 100)
        self.max_combined_length = plugin_prefs.get("maxCombinedLength", 120)

        # determine if alexa_remote_control was imported
        self.plugin_prefs["AltModuleImported"] = WAS_IMPORTED

    ########################################
    def startup(self):
        self.logger.debug("startup called")

        # show pending questions on startup
        self.show_pending_questions()  

        result = self.isAlexaPluginRunning()
        if not result["alexa_enabled"]:
            self.logger.warn(
                       "The Alexa Indigo Plugin is not enabled. "
                       "The 'Ask a Yes/No Question' Device Action requires it."
                       )

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
                {'key': 'useDeviceName', 
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
        question_text = plugin_action.get('QuestionToAsk')
        which_device = plugin_action.get('whichDevice')
        repeats = plugin_action.get('RepeatQuestion', False)
        stop_when_no = plugin_action.get('StopWhenNo', True)
        stop_when_yes = plugin_action.get('StopWhenYes', True)
        no_response = plugin_action.get('noResponseActionGroup', None)
        execute_no_response = plugin_action.get('executeNoResponse', False)

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

            # And then tell the Indigo Server to update the state:
            dev.updateStateOnServer("onOffState", new_on_state)

        else:  # Anything not implemented

            self.logger.error(f"Unknown device action: {action.deviceAction}")

    ##################################
    def responseReceived(self, answer, action, dev):
        dev = indigo.devices[action.deviceId]

        self.logger.debug("responseReceived called")

        # get current device states
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

            if response_action_group:
                # - select an action group -' was not picked by the user
                if int(response_action_group) != 0:
                    try:
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

        else:  # not found in unanswered questions

            if last_question_epoch == "Testing":
                self.confirm_test(answer, dev)

        # clear out the device states, for the next question
        dev.updateStatesOnServer([
            {'key': 'onOffState', 'value': False},
            {'key': 'LastQuestionEpoch', 'value': ''}, 
        ])

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
                use_device_name = dev.states.get("useDeviceName", "")
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
        if self.plugin_prefs.get("forTextToSpeech"):
            if plugin_action.description == 'text to speech':
                self.alexa_speak(plugin_action, dev)
                return True

            # if running as script
            elif plugin_action.description == "plugin action":

                # validate plugin_action
                if not self.validatePluginExecuteAction(plugin_action, dev):
                    return False

        # check if a Monkey and tokens are fully configured
        if not self.monkey_validation(plugin_action, dev):
            return False

        # where to say it
        monkey_id = dev.states['monkeyId']

        # what to say
        text_to_speech = plugin_action.props.get("TextToSpeech")

        # what voice to use
        selected_voice = plugin_action.props.get("selectedVoice", False)

        # remove newline characters via RegEx
        modified_text = re.sub("\n", "", text_to_speech)

        # perform Indigo variable substitution 
        substituted_text = indigo.activePlugin.substitute(modified_text)

        # replace "&" with " &amp; "
        ssml_text = re.sub("&", "&amp;", substituted_text) 

        # encoding query string
        encoded_text = quote(ssml_text)

        # build payload
        payload = {
                   "monkey_name": "-".join(monkey_id.lower().split()),
                   "say_this": encoded_text
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
        dev = indigo.devices[int(which_device)]

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

            # update key
            key = new_epoch_string

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

        # remove newline characters via RegEx
        modified_text = re.sub("\n", "", question_to_ask)

        # perform Indigo variable substitution 
        substituted_text = indigo.activePlugin.substitute(modified_text)

        # replace "&" with " &amp; "
        ssml_text = re.sub("&", "&amp;", substituted_text)

        # encoding query string
        encoded_text = quote(ssml_text)

        # get values for Voice Monkey 
        monkey_id = dev.pluginProps["monkey_id"]
        no_preset_id = dev.pluginProps["no_preset_id"]
        yes_preset_id = dev.pluginProps["yes_preset_id"]
            
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

        # remove newline characters via RegEx
        modified_url = re.sub("\n", "", audio_file_url)

        # perform Indigo variable substitution 
        substituted_url = indigo.activePlugin.substitute(modified_url)

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
        modified_url = re.sub("\n", "", audio_file_url)
        # perform Indigo variable substitution 
        substituted_url = indigo.activePlugin.substitute(modified_url)

        # what to say
        text_to_speech = plugin_action.props.get("TextToSpeech")

        # remove newline characters via RegEx
        modified_text = re.sub("\n", "", text_to_speech)

        # perform Indigo variable substitution 
        substituted_text = indigo.activePlugin.substitute(modified_text)

        # replace "&" with " &amp; "
        ssml_text = re.sub("&", "&amp;", substituted_text)  # 

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

        # where to play it
        monkey_id = dev.states['monkeyId']

        # get the name of the sound
        the_sound = plugin_action.props.get("soundName")

        # get the path of the sound to make
        sound_path = sounds.get(the_sound) 

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
            the_device = dev.pluginProps["useDeviceName"]
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

        elif plugin_action.description == "run a alexa routine by name":

            # if user wants to use an alternate name
            if dev.pluginProps["useAltName"]:
                device_name = dev.pluginProps["AltDeviceName"]
            else:  # otherwise use the device name
                device_name = dev.name

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
            # check if user wants to use an alternate name
            if dev.pluginProps.get("useAltName", False):
                device_name = dev.pluginProps["AltDeviceName"]
            else:  
                # otherwise use the default device name
                device_name = dev.name

        # what to say
        text_to_speech = plugin_action.props.get("TextToSpeech")
        selected_voice = plugin_action.props.get("selectedVoice")

        # remove newline characters via RegEx
        modified_text = re.sub("\n", "", text_to_speech)

        # perform Indigo variable substitution 
        substituted_text = indigo.activePlugin.substitute(modified_text)

        # replace "&" with " &amp; "
        ssml_text = re.sub("&", "&amp;", substituted_text)  # 

        # call alexa_speaks
        alexa_remote_control.alexa_speak(ssml_text, 
                                         device_name, 
                                         selected_voice)

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
            the_device = dev.pluginProps["useDeviceName"]
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
            device_name = dev.pluginProps["AltDeviceName"]
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
    def logging_options(self, valuesDict, typeId="", devId=None):

        errorsDict = indigo.Dict()
        max_combined_length = valuesDict.get("maxCombinedLength")
        max_text_length = valuesDict.get("maxTextLength")

        if not max_combined_length.isdigit() or int(max_combined_length) < 25:

            errorMsg = ('Invalid entry, a positive number greater than 25 '
                        'was not entered for the character length.')
            errorsDict["maxCombinedLength"] = errorMsg
            errorsDict["showAlertText"] = (
                'The minimum character value is 25. The default was 125.'
                )
        else:
            self.max_combined_length = int(valuesDict.get('maxCombinedLength'))
            self.plugin_prefs["maxCombinedLength"] = self.max_combined_length

        if not max_text_length.isdigit() or int(max_text_length) < 25:

            errorMsg = ('Invalid entry, a positive number greater than 25 '
                        'was not entered for the character length.')
            errorsDict["maxTextLength"] = errorMsg
            errorsDict["showAlertText"] = (
                'The minimum character value is 25. The default was 100.'
            )

        else:
            self.max_text_length = int(valuesDict.get('maxTextLength'))
            self.plugin_prefs["maxTextLength"] = self.max_text_length

        # check for errors  #
        if len(errorsDict) > 0:
            return (False, valuesDict, errorsDict)
        return (True, valuesDict)

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
        for d in questions:

            try:
                action = self.unanswered[d]['plugin_action']
                question = action.get('QuestionToAsk')
                which_device = action['whichDevice']

                try:
                    dev = indigo.devices[int(which_device)]
                    device_name = dev.name

                    # get the key in the device right now
                    last_question_epoch = dev.states['LastQuestionEpoch'] 

                    # was the question just asked
                    if last_question_epoch == d:
                        # remove the devices Yes/No responding Action Group
                        dev.updateStatesOnServer([
                            {'key': 'LastQuestionEpoch', 'value': ''}, 
                        ])

                except KeyError:
                    self.logger.error(
                      'The configured device with the ID '
                      f'"{which_device}", no longer exists. '
                       )
                    device_name = "Unknown"

                del self.unanswered[d]
                log_entry = (f"'{device_name}' pending question cancelled")
                text = (f"{question}") 
                self.wrapLogging(text, log_entry)

            except KeyError:
                self.logger.error(
                  f'The question key "{d}", no longer exists. ')

        else:  # when done looping
            pass

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

            ####
            # remove newline characters via RegEx
            modified_text = re.sub("\n", "", question_to_ask)

            # perform Indigo variable substitution 
            substituted_text = indigo.activePlugin.substitute(modified_text)

            # replace "&" with " &amp; "
            ssml_text = re.sub("&", "&amp;", substituted_text)  # 

            # encoding query string
            encoded_text = quote(ssml_text)

            ####

            # pick random action groups..just for validation
            action_groups = indigo.actionGroups
            execute_when_yes = random.choice(action_groups.keys())
            execute_when_no = random.choice(action_groups.keys())

            ask_yes_no = actionDict('ask a yes/no question', 
                                    'YesNoQuestion',
                                    {
                                     'whichDevice': device_id,
                                     "QuestionToAsk": ssml_text,
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
                    f"has a repeating Yes/No with {cycles - the_count} "
                    f"{one_or_more} left")

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
                    ask = re.sub("\n", "", question)
                    substituted_text = indigo.activePlugin.substitute(ask)
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
            if len(valuesDict.get("TextToSpeech", "")) < 1:
                errorsDict["TextToSpeech"] = (
                    "Enter text that is at least one character long to "
                    "use the text-to-speech feature."
                )
                self.logger.error(errorsDict["TextToSpeech"])
                errorsDict["showAlertText"] = (
                    'In the space provided, type what you want the device '
                    'to say out loud '
                    )

            change_voice = valuesDict.get("ChangeVoice", False)
            selected_voice = valuesDict.get("selectedVoice", None)

            if not change_voice:
                valuesDict["selectedVoice"] = None

            if selected_voice and selected_voice not in voices:
                errorsDict["selectedVoice"] = (
                    f"The voice '{selected_voice}' is not recognized")
                self.logger.error(errorsDict["selectedVoice"])

        def validate_play_audio_file_url(valuesDict):
            if not self._validateURL(valuesDict.get("audioFileUrl", "")):
                errorsDict["audioFileUrl"] = (
                    "Enter a publicly accessible URL. "
                    "The URL must begin with https://"
                )
                self.logger.error(errorsDict["audioFileUrl"])

        def validate_play_background_audio_file(valuesDict):
            if not self._validateURL(
                 valuesDict.get("backgroundAudioFileUrl", "")):

                errorsDict["backgroundAudioFileUrl"] = (
                    "Enter a publicly accessible URL. "
                    "The URL must begin with https://"
                )
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
            else:
                err_msg = "Please select the Device that asks the question."
                self.logger.error(err_msg)
                errorsDict["whichDevice"] = err_msg

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
            else:
                for yes_or_no in ['executeWhenYes', 'executeWhenNo']:
                    action_group = valuesDict.get(yes_or_no, False)
                    if (action_group 
                       and not self.validate_action_group_id(action_group)):

                        err_msg = ("A valid Action Group is needed for either "
                                   "the Yes or No response.")
                        self.logger.error(err_msg)
                        errorsDict[yes_or_no] = err_msg

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
                        self.logger.error(err_msg)
                else:
                    err_msg = (
                        "You must select a valid Action Group "
                        "to be executed, if the option is ticked."
                    )
                    errorsDict["noResponseActionGroup"] = err_msg
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

            result = self.isAlexaPluginRunning()
            if not result["alexa_enabled"]:
                err_msg = 'The Indigo Alexa plugin is not enabled.'
                errorsDict["QuestionToAsk"] = (err_msg)
                self.logger.error(err_msg)
                errorsDict["showAlertText"] = (
                    "To implement 'Ask a Yes/No Question', you have "
                    "to Enable the Indigo Alexa plugin."
                    )

            question_to_ask = valuesDict.get("QuestionToAsk", "")
            if not question_to_ask:
                self.logger.error(
                    "The question you want to ask has an invalid format")
                errorsDict["QuestionToAsk"] = (
                    "The question you want to ask has an invalid format")

        # Validate based on typeId
        if typeId == "PlayBackgroundAudioFile":
            validate_play_background_audio_file(valuesDict)
            validate_text_to_speech(valuesDict)

        elif typeId == "PlayAudioFile":
            validate_play_audio_file_url(valuesDict)

        elif typeId == "YesNoQuestion":
            validate_yes_no_question(valuesDict)
            validate_repeat_settings(valuesDict)
            validate_action_groups(valuesDict)
            validate_device(valuesDict)

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

        use_alexa_remote = valuesDict.get('useAlexaRemoteControl', False)
        adjust_timing = valuesDict.get('AdjustTiming', False)

        if not use_alexa_remote:
            valuesDict['forTextToSpeech'] = False
            valuesDict['forPlayingSounds'] = False

        access_token = valuesDict.get("accessToken", '')
        secret_token = valuesDict.get("secretToken", '')

        # if either access token not enter, warn the user but allow it
        if not (len(access_token) >= 1 and len(secret_token) >= 1):
            # if using the alexa_remote_control_module
            if use_alexa_remote:
                self.logger.warn(
                    'To use any function that requires the Voice Monkey API, '
                    "such as audio playback "
                    )
                self.logger.warn(
                    "or verbally prompted 'Yes or No' questions, "
                    "API Tokens are required."
                                 )
                self.logger.warn(
                    "The imported 'alexa_remote_control' module can handle "
                    "text-to-speech and sound playback, if it is set up and "
                    "configured correctly."
                                 )

            else:  # if not using the alexa_remote_control_module
                errorMsg = (
                    'Voice Monkey API Tokens are not configured correctly')
                errorsDict["accessToken"] = errorMsg
                errorsDict["secretToken"] = errorMsg
                errorsDict["showAlertText"] = (
                        'To use the Voice Monkey API, you must '
                        'enter both your Secret and Access Tokens')

        # if user wants to use an alternate name
        if use_alexa_remote:
            # prepare the error message
            errorMsg = (
                        "Additional configuration is required "
                        "before this selection is allowed. See "
                        "the documenation for more information."
                        )
            if not self.plugin_prefs.get("AltModuleImported"):
                # don't allow this configuration
                errorsDict["showAlertText"] = (errorMsg)
                errorsDict["use_alexa_remote"] = errorMsg
                self.logger.error(errorsDict["use_alexa_remote"])

        if adjust_timing:
            max_time_to_wait = valuesDict.get('maxTimeToWait')
            min_yes_no_delay = valuesDict.get('minYesNoDelay')
            sleep_time = valuesDict.get('sleepTime')
            if max_time_to_wait < 5:
                errorMsg = ('Invalid entry, a positive number greater than 5 '
                            'was not entered')
                errorsDict["maxTimeToWait"] = errorMsg
                errorsDict["showAlertText"] = (
                    'The maximum number of seconds to wait for a Yes or No '
                    'response must be a positive number greater than 5.'
                    )
            else:
                self.max_wait = int(valuesDict.get('maxTimeToWait'))

            if min_yes_no_delay < 5:
                errorMsg = ('Invalid entry, a positive number greater than 5 '
                            'was not entered')
                errorsDict["minYesNoDelay"] = errorMsg
                errorsDict["showAlertText"] = (
                    'The minimum number of seconds that must elapse before '
                    'a question can be repeated, must be a positive number '
                    'greater than 5'
                )
            else:
                self.min_delay = int(valuesDict.get('minYesNoDelay'))

            if sleep_time < 1:
                errorMsg = ('Invalid entry, value can not be less than 0.')
                errorsDict["sleepTime"] = errorMsg
                errorsDict["showAlertText"] = (
                    'Specify the number of seconds to pause between '
                    'iterations of the runConcurrentThread() function by '
                    'entering a value in the text field. The default value '
                    'is 5 seconds. '
                )
            else:
                self.sleep_time = int(valuesDict.get('sleepTime'))

        else:  # change them back to defaults unchecked
            
            self.min_delay = 35
            valuesDict['minYesNoDelay'] = 35

            self.max_wait = 30 
            valuesDict['maxTimeToWait'] = 30

            self.sleep_time = 5 
            valuesDict['sleepTime'] = 5

        # where there any errors?
        if len(errorsDict) > 0:
            return (False, valuesDict, errorsDict)
        return (True, valuesDict)

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

        if type(dev) is indigo.RelayDevice:
            device_id = dev.id
        else:
            device_id = dev

        # validate Action Config for scripting
        result = self.validateActionConfigUi(plugin_action.props, 
                                             plugin_action.pluginTypeId, 
                                             device_id)
        if not result[0]:
            return False
        else:
            return True

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
        and False if it can not, and prints a message for the uers in the log
        """

        # announce function if debugging
        self.logger.debug("monkey_validation called")

        errorsDict = indigo.Dict()

        # check if the access and secret tokens are configured
        access_token = self.plugin_prefs.get("accessToken")
        secret_token = self.plugin_prefs.get("secretToken")

        if not access_token or not secret_token:

            self.logger.error(
                'To use the Monkey Voice API, you must configure an '
                'Access Token and a Secret Token '
                ) 
            errorsDict["accessToken"] = 'Invalid'
            errorsDict["secretToken"] = 'Invalid'

        # check if a useable Monkey Id values is configured
        # could be blank if the Alternate module in use
        if type(dev) is indigo.RelayDevice:
            props = dev.pluginProps
            monkey_id = props["monkey_id"]
            if len(monkey_id) < 1:
                self.logger.error(
                    'The Voice Monkey functions are not fully configured '
                    'for this device. ')
                self.logger.error(
                    'Check the "(Voice Monkey device name)" '
                    'configured in Indigo for the selected device'
                    ) 
                errorsDict["monkey_id"] = False

        # validate if called by Yes/No Questions
        if plugin_action.pluginTypeId == 'YesNoQuestion':

            result = self.isAlexaPluginRunning()
            if not result["alexa_enabled"]:
                self.logger.error(
                       "The Alexa Indigo Plugin is not enabled. "
                       "The 'Ask a Yes/No Question' Device Action requires it."
                           )
                errorsDict["alexa_enabled"] = False

        # where there any errors?
        if len(errorsDict) > 0:
            return False
        return True

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
            # remove newline characters via RegEx
            question_to_ask = re.sub("\n", "", question)
            value = (key, f'{dev.name} - {question_to_ask}')
            values.append(value)
        return values

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

        if len(substituted_text) > self.max_text_length:
            wrapped_text = textwrap.fill(substituted_text, 
                                         self.max_text_length)
        else:
            wrapped_text = substituted_text

        combined_text = f'{log_entry} : "{wrapped_text}"'
        if len(combined_text) > self.max_combined_length:
            indigo.server.log(f'{log_entry}\n"{wrapped_text}"')
        else:
            indigo.server.log(combined_text)   

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

    def actionsWithAnExit(self, filter="", valuesDict=None, typeId="", targetId=0):  # noqa
        """
        
        Needed to provide a selection for the User after creating and saving, 
        an action, then wanting to change an Action Group value to 
        None/Nothing/Blank
        
        """
        action_group_list = [(ag.id, ag.name) for ag in indigo.actionGroups]
        sorted_list = sorted(action_group_list, key=lambda x: x[1].lower())
        sorted_list.append((0, '- select an action group -'))
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

    def isAlexaPluginRunning(self):

        # check if the Alexa Plugin is running
        alexa_id = "com.indigodomo.indigoplugin.alexa"
        alexaPlugin = indigo.server.getPlugin(alexa_id)
        alexa_enabled = alexaPlugin.isEnabled()

        return {
                "alexa_enabled": alexa_enabled
                }

    ###########################
    @staticmethod
    def _validateURL(url):
        '''
        This function validates a URL formating and only accept https://
        '''
        regex = ("^((https)://)[-a-zA-Z0-9@:%._\\+~#?&//=]{2,256}"
                 "\\.[a-z]{2,6}\\b([-a-zA-Z0-9@:%._\\+~#?&//=]*)$")

        substituted_url = indigo.activePlugin.substitute(url)
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
