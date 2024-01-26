#!/usr/bin/python

import os
import indigo
import logging
import subprocess
import shlex
from alexa_constants import sounds


SCRIPT_NAME = 'alexa_remote_control.sh'
SCRIPT_PATH = '/Library/Application Support/Perceptive Automation/Scripts/'


def does_script_exists():

    full_script_path = os.path.join(SCRIPT_PATH, SCRIPT_NAME)
    if os.path.exists(full_script_path):
        return True
    else:
        return False


def run_shell(the_parameters):
    """
    Runs a shell script with parameters and returns its output and errors.

    :param the_parameters: A list of parameters to pass to the shell script.
    :return: A tuple containing stdout and stderr of the shell script.
    """
    if not does_script_exists():
        indigo.server.log("'alexa_remote_control.sh' can not be found.",
                          level=logging.ERROR)
        return ("Additional configuration is required. ", "")

    try:
        full_script_path = os.path.join(SCRIPT_PATH, SCRIPT_NAME)
        the_parameters.insert(0, full_script_path)
        result = subprocess.run(the_parameters, 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE, 
                                text=True)
        return result.stdout, result.stderr
    except Exception as e:
        indigo.server.log(f"Error executing the script: {e}",
                          level=logging.ERROR)
        return ("", "")


def process_output(stdout, stderr, log_entry, function_name):

    # if an error received from alexa-remote-control.sh
    if 'ERROR:' in stdout:

        indigo.server.log(
            f'alexa_remote_control.sh: {stdout[stdout.find("ERROR"):]}',
            level=logging.ERROR
            )
        return False

    # was the command successfully sent
    elif 'sending cmd' in stdout:

        if function_name != 'alexa_speak':
            indigo.server.log(f'{log_entry}', f'{function_name}')
        return True

    else:  # some other problem

        # show the contents of stdout
        indigo.server.log(
            f'stdout: {stdout}', 
            level=logging.ERROR
            )
        return False

        # if stderr has a value, show that
        if stderr:
            indigo.server.log(
                f'stderr: {stderr}', 
                level=logging.ERROR
                )    
            return False


def alexa_speak(say_this, the_device, voice=''):

    if voice:
        # use SSML tags to change the voice
        speak_this_way = (
            f'speak:<speak><voice name=\'{voice}\'>{say_this}</voice></speak>')

        # format log output
        log_entry = (f'{the_device} : {voice} - {say_this}')
    else:
        # format for default voice
        speak_this_way = (f"speak:'{say_this}'")

        # format log output
        log_entry = (f'{the_device} : "{say_this}"')

    the_parameters = [
        '-d',
        '{0}'.format(the_device),
        '-e',
        speak_this_way
    ]

    stdout, stderr = run_shell(the_parameters)
    return process_output(stdout, stderr, log_entry, 'alexa_speak')


def ask_alexa(ask_this, the_device):

    # format log output
    log_entry = (f'{the_device} : Typed Request : "{ask_this}"')

    # setup the request
    the_parameters = [
        '-d',
        '{0}'.format(the_device),
        '-e',
        "textcommand:'{0}'".format(ask_this)
    ]

    stdout, stderr = run_shell(the_parameters)
    process_output(stdout, stderr, log_entry, 'ask_alexa')


def pass_device_arg(args, the_device):

    # format log output
    log_entry = (f'{the_device} : Pass Arguments : "{args}"')

    # split shell command string into a list of arguments
    the_aguments = shlex.split(args)

    # setup the request
    the_parameters = [
        '-d',
        '{0}'.format(the_device),
        
    ]

    # combine the lists
    the_parameters.extend(the_aguments)

    stdout, stderr = run_shell(the_parameters)
    process_output(stdout, stderr, log_entry, 'pass_alexa_args')


def pass_cmd_line_args(args, the_device=None):

    if the_device:
        args += f" -d '{the_device}'" 

    # format log output
    log_entry = (f'Pass Arguments : "{args}"')

    # split shell command string into a list of arguments
    the_aguments = shlex.split(args)

    stdout, stderr = run_shell(the_aguments)
    process_output(stdout, stderr, log_entry, 'pass_cmd_line_args')


def alexa_routine(routine_name, the_device):

    # format log output
    log_entry = (
        f'{the_device} : Run a Alexa Routine by Name : "{routine_name}"')

    # only speak if a device identified
    if the_device:

        the_parameters = [
            '-d',
            '{0}'.format(the_device),
            '-e', 
            "automation: {0}".format(routine_name),
        ]
        
    stdout, stderr = run_shell(the_parameters)
    process_output(stdout, stderr, log_entry, 'alexa_routine')


def list_available_devices():

    the_parameters = [
        '-a',
    ]
    
    stdout, stderr = run_shell(the_parameters)

    lookfor = ('the following devices exist in your account:')
    if 'ERROR:' in stdout:

        print(f'alexa_remote_control.sh: {stdout[stdout.find("ERROR"):]}')
        return []

    # was what we were looking for seen
    elif lookfor in stdout:
        
        # split the output and return as a list
        stdout_split = (stdout.split('\n'))
        start_index = stdout_split.index(lookfor)
        device_list = stdout_split[start_index+1:-1]

        # remove duplicates
        device_list = list(set(device_list))
        
        # create a list of tuples
        my_list_of_tuples = [(item, item) for item in device_list]

        # insert a blank, so the user can deselect
        my_list_of_tuples.insert(0, ('Default', ''))

        return my_list_of_tuples

    else:  # some other problem

        # show the contents of stdout
        print(f'stdout: {stdout}')

        # if the call stderr, show contents of stderr
        if stderr:
            print(f'stderr: {stderr}')

        return []


def alexa_play_sound(the_sound, the_device):

    # format sound 
    sound_to_play = (f"<audio src='soundbank://soundlibrary{the_sound}'/>")
    sound_name = sounds.get(the_sound)

    # format log output
    log_entry = f'{the_device}: Play a Sound : "{sound_name}"'

    # build the shell command
    the_parameters = [
        '-d',
        '{0}'.format(the_device),
        '-e',
        f"speak:'{sound_to_play}'"
    ]

    stdout, stderr = run_shell(the_parameters)
    process_output(stdout, stderr, log_entry, 'alexa_play_sound')
