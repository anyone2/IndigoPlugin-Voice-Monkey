#!/usr/bin/python

import indigo
import logging
import subprocess
import shlex


def run_shell(the_parameters):

    file_name = 'alexa_remote_control.sh'
    file_path = '/Library/Application Support/Perceptive Automation/Scripts/'

    the_parameters.insert(0, f'{file_path}{file_name}')

    with subprocess.Popen(the_parameters,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE) as p:
        output, errors = p.communicate()
    stdout = output.decode('utf-8')
    stderr = errors.decode('utf-8')

    return stdout, stderr


def process_output(stdout, stderr, log_entry, function_name):

    # if an error received from alexa-remote-control.sh
    if 'ERROR:' in stdout:

        indigo.server.log(
            f'alexa_remote_control.sh: {stdout[stdout.find("ERROR"):]}',
            level=logging.ERROR
            )

    # was the command successfully sent
    elif 'sending cmd' in stdout:

        indigo.server.log(f'{log_entry}', f'{function_name}')

    else:  # some other problem

        # show the contents of stdout
        indigo.server.log(
            f'stdout: {stdout}', 
            level=logging.ERROR
            )

        # if stderr has a value, show that
        if stderr:
            indigo.server.log(
                f'stderr: {stderr}', 
                level=logging.ERROR
                )    


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
    process_output(stdout, stderr, log_entry, 'alexa_speak')


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

    sounds = {
              'Air Horn 1': '/alarms/air_horns/air_horn_01',
              'Boing 1': '/alarms/beeps_and_bloops/boing_01',
              'Bell 1': '/alarms/beeps_and_bloops/bell_01',
              'Bell 2': '/alarms/beeps_and_bloops/bell_02',
              'Bell 3': '/alarms/chimes_and_bells/chimes_bells_05',
              'Buzzer 1': '/alarms/buzzers/buzzers_01',
              'Buzzer 2': '/alarms/buzzers/buzzers_04',
              'Chimes': '/alarms/chimes_and_bells/chimes_bells_04',
              'Ding 1': '/alarms/beeps_and_bloops/bell_03',
              'Ding 2': '/alarms/beeps_and_bloops/bell_04',
              'Doorbell 1': '/home/amzn_sfx_doorbell_01',
              'Doorbell 2': '/home/amzn_sfx_doorbell_chime_02',
              'Electronic Beep 1': '/musical/amzn_sfx_electronic_beep_01',
              'Electronic Beep 2': '/musical/amzn_sfx_electronic_beep_02',
              'Electronic Beep 3': '/scifi/amzn_sfx_scifi_timer_beep_01',
              'Intro 1': '/alarms/beeps_and_bloops/intro_02',
              'Siren 1': '/scifi/amzn_sfx_scifi_alarm_01',
              'Siren 2': '/alarms/beeps_and_bloops/buzz_03',
              'Tone 1': '/musical/amzn_sfx_test_tone_01',
              'Tone 2': '/alarms/beeps_and_bloops/tone_02',
              'Tone 3': '/alarms/beeps_and_bloops/tone_05',
              'Woosh': '/alarms/beeps_and_bloops/woosh_02',

    }

    # format sound and play sound, if not found use Air Horn 1
    sound_url = "<audio src='soundbank://soundlibrary{0}'/>"
    sound_to_play = sound_url.format(
        sounds.get(the_sound, sounds['Air Horn 1']))

    # format log output
    log_entry = f'{the_device}: Play a Sound : "{the_sound}"'

    # build the shell command
    the_parameters = [
        '-d',
        '{0}'.format(the_device),
        '-e',
        f"speak:'{sound_to_play}'"
    ]

    stdout, stderr = run_shell(the_parameters)
    process_output(stdout, stderr, log_entry, 'alexa_play_sound')
