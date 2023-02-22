# IndigoPlugin-Voice-Monkey
Plugin for the Indigo Home Automation system. 

This plugin for the [Indigo Domotics](http://www.indigodomo.com/) home automation platform allows you to control your Alexa devices from within Indigo. It works with the Voice Monkey Amazon Alexa skill which has the ability to perform text-to-speech, play preset sounds, and execute Alexa routines on an Alexa Smart device such as an Echo or Echo Dot.

## Supported Features:

- Execute an Alexa Routine
- Perform Text-To-Speech
- Play a preset sound (Chime, Doorbell, Air Horn, etc.)
- Play a URL audio file (Dogs barking, etc.)
- Play a URL audio file (Dogs barking, etc.) while performing Text-To-Speech
- Ask a Prompted Yes/No Question, executing an Action Group based on the Yes, No, or No Response. (the Alexa Plugin is a requirement)

All of these are "Pro" features of the Amazon Alexa Skill except for the ability to Execute an Alexa Routine. The "Pro" features, by the way, are $6 per year. 

Visit [https://voicemonkey.io/start](https://voicemonkey.io/start) to learn more.

With the non-Pro feature (singular), you are limited to, if you want to call it a limit, triggering Alexa routines. 

I shared some information about this skill last year in this thread: [https://forums.indigodomo.com/viewtopic.php?f=138&t=25958](https://forums.indigodomo.com/viewtopic.php?f=138&t=25958)



## Setup Instructions

Follow the instructions details on the [https://voicemonkey.io/start](https://voicemonkey.io/start):

Step 1 – Enable the Voice Monkey Skill
Step 2 – Sign In to the Voice Monkey website (to obtain API Tokens for the Plugin)
Step 3 – Create your first Monkey and routine
Step 4 – Trigger your Monkey

After following these steps, you will be able to generate your API URL and use it to trigger your monkeys either from your web browser, or from services such as IFTTT or your this plugin.


## Installlation Instructions

Download the plugin, after the plugin starts in Indigo, add your Access and Secret Tokens under Plugins -> Voice Monkey -> Configure...


## Triggering a Alexa Routine

( Describe how a monkey would be create to do this )



## Scripting

 If placed script titled 'voice_monkey.py' in Python3-Includes folder, the full is path '/Library/Application Support/Perceptive Automation/Python3-includes', you can leverage the Plugin to call various functions.

    import voice_monkey 

    voice_monkey.routine(monkeyId='routine-trigger-one', deviceId=651183378)

    voice_monkey.speak(text='It is working extremely well', deviceId=651183378)

    voice_monkey.yes_or_no(Question='Is your plugin finally working?',
                           YesActionGroupId=800994550,
                           NoActionGroupId=920250421,
                           deviceId=651183378)


