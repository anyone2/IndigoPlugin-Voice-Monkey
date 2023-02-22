# IndigoPlugin-Voice-Monkey
Plugin for the Indigo Home Automation system. 

This plugin for the [Indigo Domotics](http://www.indigodomo.com/) home automation platform allows you to control your Alexa devices from within Indigo. It works with the Voice Monkey Amazon Alexa skill which has the ability to perform text-to-speech, play preset sounds, and execute Alexa routines on an Alexa Smart device such as an Echo or Echo Dot.

## Supported Features:

- Trigger an Alexa Routine
- Perform Text-To-Speech
- Play a preset sound (Chime, Doorbell, Air Horn, etc.)
- Play a URL audio file (Dogs barking, etc.)
- Play a URL audio file (Dogs barking, etc.) while performing Text-To-Speech
- Ask a Prompted Yes/No Question, executing an Action Group based on the Yes, No, or No Response. (the Indigo Alexa Plugin is required)

All of these are "Pro" features of the Amazon Alexa Skill except for the ability to Execute an Alexa Routine. The "Pro" features, by the way, are $6 USD per year. 

Visit [https://voicemonkey.io/start](https://voicemonkey.io/start) to learn more.

With the non-Pro feature (singular), you are limited to, if you want to call it a limit, triggering Alexa routines. 


The support forum for this plugin is found here: 

## Setup Instructions

Follow the instructions details on the [https://voicemonkey.io/start](https://voicemonkey.io/start):

Step 1 – Enable the Voice Monkey Skill
Step 2 – Sign In to the Voice Monkey website (to obtain API Tokens for the Plugin)
Step 3 – Create your first Monkey and routine
Step 4 – Trigger your Monkey

After following these steps, you will be able to generate your API URL, confirm its working and use it to trigger your monkeys either from your web browser, or from services such as IFTTT or your this plugin.


## Installlation Instructions

Download the plugin, after the plugin starts in Indigo, add your Access and Secret Tokens under Plugins -> Voice Monkey -> Configure...


## Triggering a Alexa Routine

( Describe how a monkey would be create to do this )



## Scripting

 If you place the script titled 'voice_monkey.py' in Python3-Includes folder,

 full is path '/Library/Application Support/Perceptive Automation/Python3-includes'

 you can leverage the Plugin to call functions for Text-To-Speech, Executing Routines or asking Yes or No questions.

    import voice_monkey 

    voice_monkey.routine(monkeyId='routine-trigger-one', deviceId=651183378)

    voice_monkey.speak(text='It is working extremely well', deviceId=651183378)


    voice_monkey.yes_or_no(question='Is your plugin finally working?',
                           execute_when_yes=800994550,
                           execute_when_no=920250421,
                           device_id=651183378)


## One more thing...

The plugin also works with alexa_remote_control, which gives it even greater control over Amazon Alexa devices.

For more information and installation instructions see this page, [https://github.com/thorsten-gehrig/alexa-remote-control]https://github.com/thorsten-gehrig/alexa-remote-control

The configuration and installation of alexa_remote_control is optional, the Voice Monkey API skills mentioned above, will work without installing it.


## Supported Features: (with alexa_remote_control installed)

- Perform Text-To-Speech
- Play a preset sound (Chime, Doorbell, Air Horn, etc.)
- Execute an Alexa Routine (By the Name shown in the Alexa App)
- Type a Request to Alexa (Type in anything you would otherwise say to Alexa)
- Pass any command from Indigo, directly to alexa_remote_control
    - change the volume
    - pause, play, repeat
    - connect/disconnect from BlueTooth
    - etc


## Installlation Instructions

After successfully configuring alexa_remote_control, which you can test by issuing any of the available commands, there are only a few additional steps.

Place the alexa_remote_control.sh file, or a copy of it, and the alexa_remote_control.py file included in this reposisitory in the Python3-Includes folder.

The full is path '/Library/Application Support/Perceptive Automation/Python3-includes'

In Indigo, under Plugins -> Reload Libraries and Attachments
In Indigo, under Plugins -> Voice Monkey -> Reload

In the log, you "should" see the plugin indicate the alexa_remote_control module was imported.

   Starting plugin "Voice Monkey 2022.1.0" (pid 25946)
   Voice Monkey                    alexa_remote_control was imported
   Started plugin "Voice Monkey 2022.1.0"
   Voice Monkey                    There are no pending Yes/No Questions

In Indigo, under Plugins -> Voice Monkey -> Configure...

Click the checkbox for 'Use alexa-remote-control'









