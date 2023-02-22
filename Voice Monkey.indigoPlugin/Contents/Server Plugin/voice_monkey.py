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
              execute_when_yes=0, execute_when_no=0, 
              repeats=False, 
              stop_when_yes=False, stop_when_no=False,
              cycles=0, seconds=0,
              no_response=None, no_response_group=None,
              device_id=None):
    """
    This function uses Text-to-Speech to ask a Yes or No prompted Question 
    on a given device.
    
    Passed to it is Question, an Action Group id to be executed if the  
    response is Yes and an Action Group id to be executed if the response 
    is No
    """
    props = {   
        'QuestionToAsk': question, 
        'executeWhenYes': execute_when_yes, 
        'executeWhenNo': execute_when_no,  
        'executeNoResponse': no_response,  
        'noResponseActionGroup': no_response_group,  
        'RepeatQuestion': repeats,  
        'cycles': cycles,  
        'seconds': seconds,  
        'StopWhenYes': stop_when_yes,  
        'StopWhenNo': stop_when_no,
        'whichDevice': device_id,  
    }
    return ifPluginEnabledExecuteAction('YesNoQuestion', props, device_id)


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
    This function is used to play an audio file on a selected device.
    The audioFileUrl is passed is the URL location of the file.
    """    
    props = {   
        'soundName': soundName, 
    }
    return ifPluginEnabledExecuteAction('PlaySound', props, deviceId)


def play_background_audio(text, audioFileUrl, deviceId):
    """
    This function is used to play an audio file on a selected device.
    The audioFileUrl is passed is the URL location of the file.
    """    
    props = {   
        'backgroundAudioFileUrl': audioFileUrl, 
        'TextToSpeech': text, 
    }
    return ifPluginEnabledExecuteAction(
        'PlayBackgroundAudioFile', props, deviceId)


def ask_alexa(question, deviceId):
    """
    This function is used to perform Text-to-Speech on the given device.
    The text passed will be spoken by the Alexa device.
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
    This function is used to perform Text-to-Speech on the given device.
    The text passed will be spoken by the Alexa device.
    """    
    props = {   
        'monkeyId': routine,
    }
    return ifPluginEnabledExecuteAction('AlexaRoutine', props)
