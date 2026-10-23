#!/usr/bin/python

import indigo        
import logging


def ifPluginEnabledExecuteAction(function, props, deviceId=None):
    """ executeAction(actionId, deviceId, props)
    This function returns the PlugIn if it is running and 
    executes the specified action.
    """    
    CFBundleIdentifier = "com.anyone.indigoplugin.voice-monkey"
    plugin = indigo.server.getPlugin(CFBundleIdentifier)
    if plugin.isEnabled():
        try: 
            if deviceId:
                return plugin.executeAction(
                    function, deviceId=deviceId, props=props)
            else:
                return plugin.executeAction(
                    function, props=props)
        except Exception as e:
            indigo.server.log(
                f"Exception occurred: {e}", level=logging.CRITICAL)
    else:
        indigo.server.log(
            "The 'Alexa Voice Monkey' Plugin is not Enabled", 
            level=logging.CRITICAL)


def speak(text, deviceId, voice=''):
    """
    This function is used to perform Text-to-Speech on the given device.
    The text passed will be spoken by the Alexa device.
    """    
    props = {   
        'TextToSpeech': text,
        'selectedVoice': voice 
    }
    return ifPluginEnabledExecuteAction('TextToSpeech', props, deviceId)
    

def routine(monkeyId, deviceId):
    """
    This function is used to execute an Alexa routine on the given device.
    The monkey_id is passed as a property to the routine.
    """    
    props = {   
        'monkey_id': monkeyId, 
    }
    return ifPluginEnabledExecuteAction('TriggerRoutine', props, deviceId)
    

def yes_or_no(question, 
              executeWhenYes=0, executeWhenNo=0, 
              stopWhenYes=False, stopWhenNo=False,
              repeats=False, cycles=0, seconds=0,
              executeNoResponse=None, noResponseActionGroup=None,
              deviceId=None):
    """
    This function uses Text-to-Speech to ask a Yes or No prompted Question 
    on a given device.
    
    Passed to it is Question, an Action Group id to be executed if the  
    response is Yes and an Action Group id to be executed if the response 
    is No
    """
    props = {   
        'QuestionToAsk': question, 
        'executeWhenYes': executeWhenYes, 
        'executeWhenNo': executeWhenNo,  
        'executeNoResponse': executeNoResponse,  
        'noResponseActionGroup': noResponseActionGroup,  
        'RepeatQuestion': repeats,  
        'cycles': cycles,  
        'seconds': seconds,  
        'StopWhenYes': stopWhenYes,  
        'StopWhenNo': stopWhenNo,
        'whichDevice': deviceId,  
    }
    return ifPluginEnabledExecuteAction('YesNoQuestion', props, deviceId)


def cancel_yes_or_no(question, deviceId=None):
    """
    This function will cancel a specific Yes or No Question being asked 
    on a given device if it exists.
    
    Passed to it is Question and the device.
    """
    props = {   
        'question_to_cancel': question, 
        'which_device': deviceId,  
    }
    return ifPluginEnabledExecuteAction('cancelQuestion', props, deviceId)


def play_audio(audioFileUrl, deviceId):
    """
    This function is used to play an audio file on a selected device.
    The audioFileUrl is passed is the URL location of the file.
    """    
    props = {   
        'audioFileUrl': audioFileUrl, 
    }
    return ifPluginEnabledExecuteAction('PlayAudioFileUrl', props, deviceId)


def play_sound(soundName, deviceId):
    """
    This function plays a built-in Alexa soundbank sound on the selected
    device. soundName is the sound's DISPLAY NAME (e.g. 'Electronic Beep 1')
    as listed in the plugin's Play a Sound action menu.
    (R22: docstring corrected — was a copy-paste of play_audio.)
    """    
    props = {   
        'soundName': soundName, 
    }
    return ifPluginEnabledExecuteAction('PlaySound', props, deviceId)


def play_background_audio(text, audioFileUrl, deviceId):
    """
    This function speaks `text` while playing the audio file at
    `audioFileUrl` underneath it on the selected device.
    (R22: docstring clarified — TTS component was undocumented.)
    """    
    props = {   
        'backgroundAudioFileUrl': audioFileUrl, 
        'TextToSpeech': text, 
    }
    return ifPluginEnabledExecuteAction(
        'PlayBackgroundAudioFile', props, deviceId)


def ask_alexa(question, deviceId):
    """
    This function sends a typed request to Alexa via alexa_remote_control,
    as if the question had been spoken to the device (no wake word needed).
    Requires alexa_remote_control to be installed and configured.
    (R22: docstring corrected — was a copy-paste of speak.)
    """    
    props = {   
        'RequestOfDevice': question,
    }
    return ifPluginEnabledExecuteAction('TypedRequest', props, deviceId)


def alexa_speak(text, device, voice=None):
    """
    This function is used to perform Text-to-Speech on the given device.
    The text passed will be spoken by the Alexa device.
    """    
    props = {   
        'TextToSpeech': text,
        'deviceName': device,
        'selectedVoice': voice 
    }
    return ifPluginEnabledExecuteAction('AlexaSpeak', props)


def alexa_routine(routine, device=None):
    """
    This function runs an Alexa-app Routine by its EXACT name via
    alexa_remote_control.
    (R22: docstring corrected — was a copy-paste of speak.)

    LEGACY-PRESERVED LIMITATION: the `device` parameter is accepted but NOT
    passed through to the plugin (props carry only the routine name), so the
    ARC call has no device name and fails with a logged error. This has been
    broken since the original plugin (it raised NameError there); wiring the
    device through would change the behavior of existing scripts, so it is
    deliberately left as-is. Kept for signature compatibility.
    """    
    props = {   
        'monkey_id': routine,
    }
    return ifPluginEnabledExecuteAction('AlexaRoutine', props)


def pass_cmd_line_args(arguments, deviceId=None):
    """
    This function passes raw command-line arguments straight to
    alexa_remote_control.sh (advanced use; see the ARC documentation).
    (R22: docstring corrected — was a copy-paste of speak.)

    LEGACY-PRESERVED LIMITATION: `deviceId` is accepted but ignored
    (the call hardcodes deviceId=None). Kept for signature compatibility;
    use a '-d <device>' argument inside `arguments` instead.
    """    
    props = {   
        'arguments': arguments,
        
    }
    return ifPluginEnabledExecuteAction('PassArgs', props, deviceId=None)
