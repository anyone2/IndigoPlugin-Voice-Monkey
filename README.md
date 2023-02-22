# IndigoPlugin-Voice-Monkey

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


The support forum for this plugin is located here: [https://forums.indigodomo.com/viewforum.php?f=157](https://forums.indigodomo.com/viewforum.php?f=157)

## Voice Monkey Skill Setup Instructions

Follow the instructions details on the [https://voicemonkey.io/start](https://voicemonkey.io/start):

1. Enable the Voice Monkey Skill
2. Sign In to the Voice Monkey website (to obtain API Tokens for the Plugin)
3. Create your first Monkey and routine
4. Trigger your Monkey

After following these steps, you will be able to generate a URL, confirm that it is working, and use it to trigger your monkeys from either your web browser or from services such as IFTTT or this plugin.


## Indigo Plugin Installlation Instructions

Download the plugin, after the plugin starts, add your Voice Monkey Access and Secret Tokens under Plugins -> Voice Monkey -> Configure...


## Triggering a Alexa Routine

( Describe how a monkey would be create to do this )


## Ask a Prompted Yes/No Question (Pro feature)

( Describe how a monkey would be create to do this )

Get the basic features working before you attempt this, this process involves multiple steps and it is important to know, that Text-To-Speech works at a minimum. 

This abiliity also requires that you enable the Indigo Alexa Plugin.

- Decide which device you have created will ask the question. Simple enough. 
- Within the Indigo Alexa Plugin
    - Plugins -> Alexa -> Manage Alexa Device Publications...
    - Select the device that you want to be able to ask Yes or No questions
    - Click the checkbox 'Publish device'
    - Select as the Type: 'Switch'
    - click 'Save'
    - click 'Close'

(Describe the required configuration on the Voice Monkey Website)


## Scripting

 If you place the file titled 'voice_monkey.py' in your Python3-Includes folder,

 the full is path **'/Library/Application Support/Perceptive Automation/Python3-includes'**

 you can leverage the Plugin to call functions for Text-To-Speech, Executing Routines or asking Yes or No questions.

    import voice_monkey 

    voice_monkey.routine(monkeyId='routine-trigger-one', deviceId=651183378)


    voice_monkey.yes_or_no(question='Is your plugin finally working?',
                           execute_when_yes=800994550,
                           execute_when_no=920250421,
                           device_id=651183378)

    voice_monkey.speak(text='It is working extremely well.', deviceId=651183378)


## "One more thing..."

The plugin also works with alexa_remote_control, which gives it even greater control over Amazon Alexa devices.

For more information and installation instructions see this page, 

[https://github.com/thorsten-gehrig/alexa-remote-control](https://github.com/thorsten-gehrig/alexa-remote-control)

The configuration and installation of alexa_remote_control is optional, the Voice Monkey API skills mentioned above, will all work without installing it.


## Supported Features: (with alexa_remote_control installed)

- Perform Text-To-Speech
- Play a preset sound (Chime, Doorbell, Air Horn, etc.)
- Execute an Alexa Routine (By the name shown in the Alexa App)
- Type a Request to Alexa (Type in anything you would otherwise say to Alexa)
- Pass any command from Indigo, directly to alexa_remote_control
    - change the volume
    - pause, play, repeat
    - connect/disconnect from BlueTooth
    - etc.


## Additional Indigo Plugin Installlation Instructions

After successfully configuring alexa_remote_control, which you can test by issuing any of the available commands, there are only a few additional steps.

- Place the alexa_remote_control.sh file you downloaded and modified as part of the instructions here [https://github.com/thorsten-gehrig/alexa-remote-control](https://github.com/thorsten-gehrig/alexa-remote-control), or a copy of it, and the alexa_remote_control.py file included in this reposisitory in the Python3-Includes folder.

The full is path '/Library/Application Support/Perceptive Automation/Python3-includes'

- In Indigo, under Plugins -> Reload Libraries and Attachments
- In Indigo, under Plugins -> Voice Monkey -> Reload

In the log, you "should" see the plugin indicate the alexa_remote_control module was imported.

    Starting plugin "Voice Monkey 2022.1.0" (pid 25946)
    Voice Monkey                    alexa_remote_control was imported
    Started plugin "Voice Monkey 2022.1.0"
    Voice Monkey                    There are no pending Yes/No Questions

- In Indigo, under Plugins -> Voice Monkey -> Configure...

- Click the checkbox for 'Use alexa-remote-control'

Now test to ensure it works. Create an Action Group, select a Voice Monkey Actions and then select 'Pass command line arguments'

- Type in some command that can be executed by a device near by. 
    - for example, -d 'Family Room Echo' -e speak:'Hello world!'







