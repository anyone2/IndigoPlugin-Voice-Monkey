# IndigoPlugin-Voice-Monkey

This plugin is for the [Indigo Domotics](http://www.indigodomo.com/) home automation platform and allows you to control your Alexa devices from within Indigo. It works with the Voice Monkey Amazon Alexa skill which has the ability to perform text-to-speech, play preset sounds, and execute Alexa routines on an Alexa Smart device such as an Echo or Echo Dot.

## Supported Features:

- Trigger an Alexa Routine
- Perform Text-To-Speech
- Play a preset sound (Chime, Doorbell, Air Horn, etc.)
- Play a URL audio file (Dogs barking, etc.)
- Play a URL audio file (Dogs barking, etc.) while performing Text-To-Speech
- Ask a Prompted Yes/No Question, executing an Action Group based on the Yes, No, or No Response. (the Indigo Alexa Plugin is required)

All of these are "Pro" features of the Amazon Alexa Skill except for the ability to Trigger an Alexa Routine. The "Pro" features, by the way, are $6 USD per year. 

Visit [https://voicemonkey.io/start](https://voicemonkey.io/start) to learn more.

With the non-Pro feature (singular), you are limited to, if you want to call it a limit, triggering Alexa routines. 

The support forum for this plugin is located here: [https://forums.indigodomo.com/viewforum.php?f=157](https://forums.indigodomo.com/viewforum.php?f=157)


## Additional capabilities worth mentioning:

- Speech Synthesis Markup Language (SSML) is supported in Text-To-Speech
- Multiple voices are available to choose from for Text-To-Speech
- Indigo variable substitution is supported in Text-To-Speech and file name fields
    - %%v:12345%% for variables and %%d:12345:someStateId%% for device 


## Voice Monkey Skill Setup Instructions

Follow the instructions details on the [https://voicemonkey.io/start](https://voicemonkey.io/start):

1. Enable the Voice Monkey Skill
2. Sign In to the Voice Monkey website (to obtain API Tokens for the Plugin)
3. Create your first Monkey and routine
4. Trigger your Monkey

After following these steps, detailed on the Voice Monkey site, you will be able to generate a URL, confirm that it is working, and use it to trigger your monkeys from either your web browser or from services such as IFTTT or this plugin.


## Indigo Plugin Installlation Instructions

Download the plugin, after the plugin starts, add your Voice Monkey Access and Secret Tokens under Plugins -> Voice Monkey -> Configure...


## Triggering a Alexa Routine

( Describe how a monkey would be created to do this )


## Ask a Prompted Yes/No Question (a Pro feature)

( Describe how a monkey would be created to do this )

Get the basic features working before you attempt to set this up. This process involves multiple steps and it is important to know, that Text-To-Speech at a minimum is working.

This feature requires that you enable the Indigo Alexa Plugin.

- Decide which device you have created will ask the question. 
- Within the Indigo Alexa Plugin
    - Plugins -> Alexa -> Manage Alexa Device Publications...
    - Select the device that you want to be able to ask Yes or No questions
    - Click the checkbox 'Publish device'
    - Select as the Type: 'Switch'
    - click 'Save'
    - click 'Close'

(Describe the required configuration on the Voice Monkey Website)


## Basic Scripting

 If you place the file named 'voice_monkey.py' in your Python3-Includes folder,

 the full is path **'/Library/Application Support/Perceptive Automation/Python3-includes'**

 you can leverage the Plugin to call functions for Text-To-Speech, Triggering Routines, playing sounds or asking Yes or No questions.

    import voice_monkey 

    voice_monkey.routine(monkeyId='routine-trigger-one', deviceId=651183378)

    voice_monkey.play_sound(soundName=the_sound, deviceId=651183378)

    dogs_barking = 'https://dl.dropboxusercontent.com/s/dqk73c2cduxjg6k/one_dog_barking_audacity.mp3?dl=1'
    voice_monkey.play_audio(audioFileUrl=dogs_barking, deviceId=651183378)


    say_this = ('I am not sure why you would want to talk over dogs barking. <break time="5s"/>But you could if you really wanted to but again, I am not really sure why you would do this.<break time="7s"/>')

    dogs_barking = 'https://dl.dropboxusercontent.com/s/dqk73c2cduxjg6k/one_dog_barking_audacity.mp3?dl=1'

    voice_monkey.play_background_audio(
            text=say_this, audioFileUrl=dogs_barking, deviceId=651183378)



    voice_monkey.yes_or_no(question=ask_this, 
                           executeWhenYes=800994550, 
                           executeWhenNo=None, 
                           deviceId=651183378)

    voice_monkey.speak(text='It is working extremely well.', deviceId=651183378)


## "One more thing..."

The plugin also works with alexa_remote_control, which gives it even greater control over Amazon Alexa devices.

For more information and installation instructions see the following page: 

[https://github.com/thorsten-gehrig/alexa-remote-control](https://github.com/thorsten-gehrig/alexa-remote-control)

The configuration and installation of alexa_remote_control is optional, the Voice Monkey API skills mentioned above, will all work without installing it.


## Supported Features: (with alexa_remote_control installed)

- Perform Text-To-Speech
- Play a preset sound (Chime, Doorbell, Air Horn, etc.)
- Execute an Alexa Routine (By the name shown in the Alexa App)
- Type a Request to Alexa (Type in **anything** you would otherwise say to Alexa)
- Pass commands from Indigo, directly to alexa_remote_control
    - change the volume
    - pause, play, repeat
    - connect/disconnect from BlueTooth
    - etc.


## Additional Indigo Plugin Installlation Instructions

After successfully configuring alexa_remote_control, which you can test by issuing any of the available commands from the command line, there are only a few additional steps.

- Place the alexa_remote_control.sh file you downloaded and modified as part of the instructions found here [https://github.com/thorsten-gehrig/alexa-remote-control](https://github.com/thorsten-gehrig/alexa-remote-control), or a copy of it, and the alexa_remote_control.py file included in this reposisitory in the Python3-Includes folder.

The full is path '/Library/Application Support/Perceptive Automation/Python3-includes'

- In Indigo, under Plugins -> Reload Libraries and Attachments
- In Indigo, under Plugins -> Voice Monkey -> Reload

In the Indigo log, the plugin "should" now indicate the alexa_remote_control module was imported.

    Starting plugin "Voice Monkey 2022.1.0" (pid 25946)
    Voice Monkey                    alexa_remote_control was imported
    Started plugin "Voice Monkey 2022.1.0"
    Voice Monkey                    There are no pending Yes/No Questions

- In Indigo, under Plugins -> Voice Monkey -> Configure...

- Click the checkbox for 'Use alexa-remote-control'

Now test to ensure it works. Create an Action Group, select Voice Monkey Actions and then select 'Pass command line arguments'

- Type in some command that can be executed by a device near by. 
    - for example, -d 'Family Room Echo' -e speak:'Hello world!'

## Advanced Scripting

If everything is working up to this point, you will be able to leverage the Plugin to call alexa_remote_control functions

    import alexa_remote_control

    ask_this = 'How many days until christmas?' 
    alexa_remote_control.ask_alexa(ask_this, "Loft Echo")

    say_this = 'Only a few more days until February 9th.' 
    alexa_remote_control.alexa_speak(say_this, "Loft Echo", 'Aditi')

    alexa_remote_control.alexa_play_sound('Bell 2', 'Loft Echo')




