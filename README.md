# IndigoPlugin-Voice-Monkey

This plugin is for the [Indigo Domotics](http://www.indigodomo.com/) home automation platform and allows you to control your Alexa devices from within Indigo. It works with the [Voice Monkey - Smart Home + Routine Triggers + TTS Alexa Skill](https://www.amazon.com/TopVoiceApps-com-Voice-Monkey/dp/B08C6Z4C3R) which has the ability to perform text-to-speech, play preset sounds, and execute Alexa routines on an Alexa Smart device such as an Echo or Echo Dot.


## Supported Features:

- Trigger an Alexa Routine
- Perform Text-To-Speech
- Play a preset sound (Chime, Doorbell, Air Horn, etc.)
- Play a URL audio file (Dogs barking, etc.)
- Play a URL audio file (Dogs barking, etc.) while performing Text-To-Speech
- Ask a Prompted Yes/No Question, executing an Action Group based on the Yes, No, or No Response. (the [Indigo Alexa Plugin](https://wiki.indigodomo.com/doku.php?id=indigo_2022.2_documentation:plugins:alexa) and [Indigo Smart Home Skill](https://www.amazon.com/Indigo-Domotics-Smart-Home-Skill/dp/B097GBHBZG/ref=sr_1_1?keywords=indigo&qid=1677604743&s=digital-skills&sr=1-1) are required)

The Free features of the [Voice Monkey - Smart Home + Routine Triggers + TTS Alexa Skill](https://www.amazon.com/TopVoiceApps-com-Voice-Monkey/dp/B08C6Z4C3R) now includes Trigging Alexa Routines and Text-To-Speech. Ask a Prompted Yes/No Question **may** work in the Free version.



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

![](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/UserInterface/Configure%20Trigger%20Routine%20-%20User%20Interface.png)

---

## Creating a Device


[Step-by-Step Guide](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/DEVICE_TEXT_ONLY.md)

[Step-by-Step Guide with screenshots](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/DEVICES.md)

![](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/UserInterface/Configure%20Voice%20Monkey%20Device.png)

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

![](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/UserInterface/Configure%20Text%20to%20Speech%20-%20User%20Interface.png)



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

![](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/UserInterface/Configure%20Ask%20a%20Yes:No%20Question%20-%20User%20Interface.png)


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

Please use version v0.20d of the project file, [available here](https://github.com/thorsten-gehrig/alexa-remote-control/blob/67610c7b282ff2b45b2b39d6713890abef38e463/alexa_remote_control.sh). This version is compatible with macOS and contains all the features of the project. Note that version v0.20e, released on 2022-06-29, is not compatible with macOS and does not offer any additional features compared to v0.20d.

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

After you placed the files in the folders shown above:

- In Indigo, under Plugins -> Reload Libraries and Attachments
- In Indigo, under Plugins -> Voice Monkey -> Reload


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

![](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/UserInterface/Configure%20Type%20in%20a%20Request%20-%20User%20Interface.png)

![](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/UserInterface/Configure%20Run%20Alexa%20Routine%20By%20Name%20-%20User%20Interface.png)


## A walk thru of the setup of alexa-remote-control

I documented a walk-through of the installation and configuration of the Alexa Remote Control Project, which foor the macOS requires version 0.2d of the project file.

There are Four steps:

1. Install Homebrew and then use Homebrew to install JQ
    - [Homebrew](https://brew.sh/)
2. Download, modify, and then run **alexa-cookie-cli-macos-x64**
    - [alexa-cookie-cli](https://github.com/adn77/alexa-cookie-cli)
3. Download, modify, and then run v0.20d of **alexa_remote_control.sh**
    - [alexa_remote_control.sh](https://github.com/thorsten-gehrig/alexa-remote-control/blob/67610c7b282ff2b45b2b39d6713890abef38e463/alexa_remote_control.sh)
4. Place **alexa_remote_control.py** and **alexa_constants.py** in the Python3-includes folder
    - [Voice Monkey Plugin](https://github.com/anyone2/IndigoPlugin-Voice-Monkey)


# 1. Install Homebrew and then use Homebrew to install JQ

The Alexa Remote Control project is based on BASH and uses JQ to efficiently parse JSON. The easiest way to install JQ is with Homebrew.

The [Homebrew](https://brew.sh/) website provides the command to install Homebrew, which is shown below. 

    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

After finishing, you need to follow the instructions shown on the screen to add Homebrew to your PATH. The instructions should look something like this, but please note this is not the actual command for your system:

    (echo; echo 'eval "$(/usr/local/bin/brew shellenv)"') >> /Users/####/.zprofile
    eval "$(/usr/local/bin/brew shellenv)"

After Homebrew is installed, in the terminal, you can install JQ with the command:

    brew install jq

You can confirm JQ is installed with the command:

    jq 

And you can find out where JQ was installed with the command:

    whereis jq

# 2. Download, modify, and then run alexa-cookie-cli-macos-x64

The project requires a session cookie to run. The script, **alexa-cookie-cli-macos-x64**, is able to assist with that by providing a REFRESH\_TOKEN. This script only needs to be run once and on any machine.  

The current version is available here [https\://github.com/adn77/alexa-cookie-cli/releases/tag/v5.0.1,](https://github.com/adn77/alexa-cookie-cli/releases/tag/v5.0.1) download the file "alexa-cookie-cli-macos-x64"  


Once downloaded, change the permissions to make the file executable\:   

    chmod 755 alexa-cookie-cli-macos-x64  

run the executable, with options requesting the web page to be presented in English  

    ./alexa-cookie-cli-macos-x64 -a en_US -L en_US

You likely will see the following message when you attempt to run the file  

**zsh\: permission denied\: alexa-cookie-cli-macos-x64**  

An error window should also appear which says; "alexa-cookie-cli-macos-x64" cannot e opened because the developer cannot be verified.  macOS cannot verify that this app is free from malware."


Click Cancel  

Go to, System Preferences -\> Privacy & Security -\> "Click Allow Anyway"  

Where you see; "alexa-cookie-cli-macos-x64 was blocked from use because it is not from an identified developer"  


Go back to terminal and issue the command again  

    ./alexa-cookie-cli-macos-x64 -a en_US -L en_US


An error window should also appear which says; "macOS cannot verify the developer of "alexa-cookie-cli-macos-x64". Are you sure you want to open it? By opening this app, you will be overriding system security which can expose your computer and personal inforrmation to malware that may harm your Mac or compromise your privacy."  


**Click "Open"**

When successfully ran, you will see the following message in the terminal.  

**Error\: Please open http\://127.0.0.1\:8080/ with your browser and login to Amazon. The cookie will be output here after successfull login. / null**  

Paste URL \(http\://127.0.0.1\:8080/\) into a web browser and then log into your Amazon account on the supplied web page.  



Once you successfully log in, you'll see this message in the browswer:  

**Amazon Alexa Cookie successfully retrieved. You can close the browser.**  

Go back to terminal, CONTROL-C to exit  

Copy and store the refreshToken which will be shown and should begin with 'Atnr|.........'  

    refreshToken: Atnr|EwICIOOqYSwdviUTUzP1XzhPANwQhzoaL14GsP7zq............

# 3. Download, modify, and then run v0.20d of alexa_remote_control.sh

The macOS compatible version of the project file **alexa_remote_control.sh**, v0.20d, is available at the following link. The easiest way to download it is to click the icon for "Download raw file".
<https://github.com/thorsten-gehrig/alexa-remote-control/blob/67610c7b282ff2b45b2b39d6713890abef38e463/alexa_remote_control.sh>  

Place this file in the **'/Library/Application Support/Perceptive Automation/Script'** folder.  

In an editor, on line 103, comment out this line  

    #SET_LANGUAGE='de,en-US;q=0.7,en;q=0.3'

On line 104, uncomment this line  

    SET_LANGUAGE='en-US'

On line 108, comment out this line  

    #SET_AMAZON='amazon.de'

On line 109, uncomment out this line  

    SET_AMAZON='amazon.com'

On line 132, change the path to the JQ file which was determined earlier with the **whereis** command.  

    SET_JQ='/usr/local/bin/jq'

On line 101, paste in your Refresh Token  

    SET_REFRESH_TOKEN='Atnr|EwICIOOqYSwdviUTUzP1XzhPANwQhzoaL14GsP7zq............' 

Exit and save the **alexa_remote_control.sh** file

update the permissions on the **alexa\_remote\_control.sh** with the command\:     

    chmod 755 alexa_remote_control.sh


You can test if **alexa\_remote\_control.sh** can be run with the following command  

    ./alexa_remote_control.sh -a



# 4. Place alexa_remote_control.py and alexa_constants.py in the Python3-includes folder

Download the **alexa\_remote\_control.py** <https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Voice%20Monkey.indigoPlugin/Contents/Server%20Plugin/alexa_remote_control.py>  

Download the **alexa\_remote\_control.py** <https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Voice%20Monkey.indigoPlugin/Contents/Server%20Plugin/alexa_constants.py>  

Place both files in the '/Library/Application Support/Perceptive Automation/Python3-includes' folder  



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


