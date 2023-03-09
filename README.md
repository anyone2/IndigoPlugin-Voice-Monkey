# IndigoPlugin-Voice-Monkey

This plugin is for the [Indigo Domotics](http://www.indigodomo.com/) home automation platform and allows you to control your Alexa devices from within Indigo. It works with the [Voice Monkey - Smart Home + Routine Triggers + TTS Alexa Skill](https://www.amazon.com/TopVoiceApps-com-Voice-Monkey/dp/B08C6Z4C3R) which has the ability to perform text-to-speech, play preset sounds, and execute Alexa routines on an Alexa Smart device such as an Echo or Echo Dot.


## Supported Features:

- Trigger an Alexa Routine
- Perform Text-To-Speech
- Play a preset sound (Chime, Doorbell, Air Horn, etc.)
- Play a URL audio file (Dogs barking, etc.)
- Play a URL audio file (Dogs barking, etc.) while performing Text-To-Speech
- Ask a Prompted Yes/No Question, executing an Action Group based on the Yes, No, or No Response. (the [Indigo Alexa Plugin](https://wiki.indigodomo.com/doku.php?id=indigo_2022.2_documentation:plugins:alexa) and [Indigo Smart Home Skill](https://www.amazon.com/Indigo-Domotics-Smart-Home-Skill/dp/B097GBHBZG/ref=sr_1_1?keywords=indigo&qid=1677604743&s=digital-skills&sr=1-1) are required)

All of these are "Pro" features of the [Voice Monkey - Smart Home + Routine Triggers + TTS Alexa Skill](https://www.amazon.com/TopVoiceApps-com-Voice-Monkey/dp/B08C6Z4C3R) except for the ability to Trigger an Alexa Routine. 

The "Pro" features, by the way, are $6 USD per year. With the non-Pro feature (singular), you are limited to, if you want to call it a limit, triggering Alexa routines. 


Visit [https://voicemonkey.io/start](https://voicemonkey.io/start) to learn more.

The support forum for this plugin is located here: [https://forums.indigodomo.com/viewforum.php?f=157](https://forums.indigodomo.com/viewforum.php?f=157)


## Additional capabilities worth mentioning:

- Speech Synthesis Markup Language (SSML) is supported in Text-To-Speech
- Indigo variable substitution is supported in the Text-To-Speech fields and Audi File URL field
    - i.e. %%v:12345%% for variables and %%d:12345:someStateId%% for device states 
- Multiple voices are available to choose from for Text-To-Speech 
    - the voice for the 'Yes or No prompt', unfortunately can not be changed


## Voice Monkey Skill Setup Instructions

Follow the instructions detailed here [https://voicemonkey.io/start](https://voicemonkey.io/start):

1. Enable the Voice Monkey Skill
2. Sign-in to the Voice Monkey website (to obtain your API Tokens used by the Plugin)


## Indigo Voice Monkey Plugin Installlation Instructions

1. Download the plugin
2. After the plugin starts
    - Add your Voice Monkey Access and Secret Tokens 
        - under Plugins -> Voice Monkey -> Configure...


## Triggering a Alexa Routine (virtual triggers)

[Step-by-Step Guide](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/TRIGGERS_TEXT_ONLY.md)

[Step-by-Step Guide with screenshots](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/TRIGGERS.md)


If you are using the above guides to only configure a virtual trigger, below is an example URL demonstrating how to activate a trigger named 'Routine Trigger One' from a web browser. The monkey name, which is shown at the end of the URL as 'routine-trigger-one', should be the lowercase version of the trigger name found on the Voice Monkey website. Ensure that there are dashes inserted between the words in the monkey name. This URL can be used to test your virtual trigger and ensure that it is functioning as expected.

Example URL:

    https://api.voicemonkey.io/trigger?access_token=ACCESS_TOKEN&secret_token=SECRET_TOKEN&monkey=routine-trigger-one

---

## Creating a Device


[Step-by-Step Guide](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/DEVICE_TEXT_ONLY.md)

[Step-by-Step Guide with screenshots](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/DEVICES.md)


After creating a device, no additional configuration is need to perform **Text-To-Speech**, **Play a Sound**, **Play a Audio File** or **Play a Background Audio File** 

To perform a function:

- Create an Action Group
- Type: Device Actions

Select: 

- Voice Monkey Controls -> Text to Speech
- Voice Monkey Controls -> Play a Sound
- Voice Monkey Controls -> Play a Audio File
- Voice Monkey Controls -> Play a Background Audio File

Then:

- Select a configured Voice Monkey device
- Populate the 'configure...' window for your selection


## Ask a Prompted Yes/No Question

To use this capability, follow these steps:

1. Create a Device ([Step-by-Step Guide](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/DEVICE_TEXT_ONLY.md)) or ([Step-by-Step Guide with screenshots](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/DEVICES.md))
2. Install the [Indigo Smart Home Skill](https://www.amazon.com/Indigo-Domotics-Smart-Home-Skill/dp/B097GBHBZG/ref=sr_1_1?keywords=indigo&qid=1677604743&s=digital-skills&sr=1-1) from the Amazon Alexa Skills Store.
3. Enable the [Indigo Alexa Plugin](https://wiki.indigodomo.com/doku.php?id=indigo_2022.2_documentation:plugins:alexa) in Indigo.
4. Verify that the plugin is properly configured and functioning.
5. Follow one of the Step-by-Step Guides shown below.

[Step-by-Step Guide](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/YESNO_QUESTIONS_TEXT_ONLY.md)

[Step-by-Step Guide with screenshots](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/YESNO_QUESTIONS.md)


To perform this function:

- Create an Action Group
- Type: Device Actions

Select:

- Voice Monkey Controls -> Ask a Yes/No Question

Then:

- Populate the 'Configure Ask a Yes/No Question' window


## Basic Scripting

Place the file named 'voice_monkey.py' in your Python3-Includes folder.

The full path is **'/Library/Application Support/Perceptive Automation/Python3-includes'**


    import voice_monkey 

    # indigo.devices[651183378] # "Loft Echo"

    indigo.device.beep(651183378)

    voice_monkey.routine(monkeyId='routine-trigger-one', deviceId=651183378)

    voice_monkey.play_sound(soundName=the_sound, deviceId=651183378)

    dogs_barking = 'https://dl.dropboxusercontent.com/s/dqk73c2cduxjg6k/one_dog_barking_audacity.mp3?dl=1'
    voice_monkey.play_audio(audioFileUrl=dogs_barking, deviceId=651183378)

    say_this = ('I am not sure why you would want to talk over dogs barking. <break time="5s"/>But you could if you really wanted to but again, I am not really sure why you would do this.<break time="7s"/>')
    dogs_barking = 'https://dl.dropboxusercontent.com/s/dqk73c2cduxjg6k/one_dog_barking_audacity.mp3?dl=1'
    voice_monkey.play_background_audio(
            text=say_this, audioFileUrl=dogs_barking, deviceId=651183378)

    ask_this 'Is this plugin working out for you?'
    voice_monkey.yes_or_no(question=ask_this, 
                           executeWhenYes=800994550, 
                           executeWhenNo=None, 
                           deviceId=651183378)

    voice_monkey.speak(text='Yes, it is working extremely well.', deviceId=651183378)


## "One more thing..."

The Voice Monkey plugin is also compatible with 'alexa_remote_control', which provides additional control over Amazon Alexa devices.

For more information and installation instructions for 'alexa_remote_control', please visit the following page: [https://github.com/thorsten-gehrig/alexa-remote-control](https://github.com/thorsten-gehrig/alexa-remote-control). Note that the installation and configuration of 'alexa_remote_control' is optional - the Voice Monkey capabilities mentioned earlier will work without it.

Use the 2022-02-04: v0.20d version of the project file found [here](https://github.com/thorsten-gehrig/alexa-remote-control/blob/67610c7b282ff2b45b2b39d6713890abef38e463/alexa_remote_control.sh), the latest version, 2022-06-29: v0.20e is not compatible with macOS.

## Supported Features: (with alexa_remote_control installed)

- Perform Text-To-Speech
- Play a preset sound (Chime, Doorbell, Air Horn, etc.)
- Trigger an Alexa Routine (by the name shown in the Alexa App)
- Type a Request to Alexa (Type in **anything** you would otherwise say to Alexa)
- Pass commands from Indigo, directly to alexa_remote_control
    - change the volume
    - pause
    - play
    - repeat
    - connect/disconnect from BlueTooth
    - etc.


## Additional Indigo Plugin Installlation Instructions

After configuring **alexa_remote_control**, which you can test using available commands from the macOS command line, only a few more steps are needed.

- Place the **alexa_remote_control.sh** file you downloaded and modified as part of the instructions found here [https://github.com/thorsten-gehrig/alexa-remote-control](https://github.com/thorsten-gehrig/alexa-remote-control), or a copy of it, in the **'/Library/Application Support/Perceptive Automation/Script'** folder.

Place the **alexa_remote_control.py** file included in this reposisitory, into the Python3-Includes folder.

The full path is **'/Library/Application Support/Perceptive Automation/Python3-includes'**

## IMPORTANT: Do not move either of these files until after you get alexa_remote_control.sh working.

After you placed the files in the folders shown above:

- In Indigo, under Plugins -> Reload Libraries and Attachments
- In Indigo, under Plugins -> Voice Monkey -> Reload

In the Indigo log, the plugin "should" now indicate the **alexa_remote_control** module was imported.

    Starting plugin "Voice Monkey 2022.1.0" (pid 25946)
    Voice Monkey                    alexa_remote_control was imported
    Started plugin "Voice Monkey 2022.1.0"
    Voice Monkey                    There are no pending Yes/No Questions

- In Indigo, under Plugins -> Voice Monkey -> Configure...

- Click the checkbox for 'Use alexa-remote-control'

To test your installation and configuration, create an Action Group. Select Voice Monkey Actions and then select 'Pass command line arguments'

- Type in some command that can be executed and heard on a nearby device.
    - for example, -d 'Family Room Echo' -e speak:'Hello world!'

IMPORTANT: This command should also work from the macOS command line.

## Usage

To perform a function:

- Create an Action Group

Select: 

- Type: Voice Monkey Controls -> Type in a Request
- Type: Voice Monkey Controls -> Run an Alexa Routine by Name
- Type: Voice Monkey Controls -> Pass command line arguments
- Type: Voice Monkey Controls -> pass -d device |arg|

Then:

- Select a configured Voice Monkey device (if required)
- Populate the 'configure...' window for your selection


## Additional Scripting

If everything is working up to this point, you will be able to, from Indigo, call **alexa_remote_control** functions

    import alexa_remote_control

    # indigo.devices[651183378] # "Loft Echo"

    ask_alexa_this = 'How many days until christmas?' 
    alexa_remote_control.ask_alexa(ask_alexa_this, "Loft Echo")

    say_this = 'Its only a few more days until christmas' 
    alexa_remote_control.alexa_speak(say_this, "Loft Echo", 'Aditi')

    alexa_remote_control.alexa_play_sound('Bell 2', 'Loft Echo')

    alexa_remote_control.pass_cmd_line_args("-d 'Loft Echo' -e speak:'Hello world!'")

    routine_name = "Loft: Morning Routine"
    alexa_remote_control.alexa_routine(routine_name, "Loft Echo")





