# Creating a Voice Monkey Trigger

## A 19 step guide of how to execute a Alexa Routine which plays a fun fact

## 1) [Log into the Voice Monkey site](https://voicemonkey.io/start) 

## 2) Click 'Manage Devices'

## 3) Click 'Add a trigger'

## 4) Type in a Trigger/Routine name

If this is your first trigger, use the suggested name of 'Routine Trigger One', or create your own name

## 5) The trigger will be shown in the list, 'Routine Trigger One'

# In the Alexa App

The trigger you just created, is shown under 'Activity', 'Routine Trigger One'

## 6) Tap 'More', at the bottom of the screen

## 7) Tap Routines

## 8) Tap the " + ", to create a New Routine

## 9) On the New Routine screen, tap 'When this happens'

## 10) Tap Smart Home

## 11) Find and then tap on the name of the trigger you created at step 4, 'Routine Trigger One', then Click Save

## 12) Tap, 'Add action'

## 13) Tap 'Alexa Says'

## 14) Tap 'Tell me a fun fact'

## 15) A confirmation screen is shown, tap next

## 16) Tap, 'Choose Device'

Select a nearby Echo device, that will play a 'fun fact'

## 17) Click Save in the upper right

The routine you created is now displayed in the Routines List

# In Indigo

## 18) Create an Action Group in Indigo

Action Groups -> New

Type: Device Actions -> Voice Monkey Controls -> Trigger a Routine

## 19) In the field, 'Preset Monkey ID', type the trigger name, created at step 4, 'Routine Trigger One', then click 'Save'

This window, 'Configure Trigger a Routine' should indicate that Trigger can be found on the Voice Monkey website under Routine Triggers. It will be reworded in a future release.

## 20) Once you execute the Action Group, the log will look similiar to this and a Fun Fact should be played on the Echo device you selected at step 16

	Feb 26, 2023 at 4:12:52 PM
		Action Group                    Triggering - 'Routine Trigger One'
		Voice Monkey                    Trigger a Routine : "Routine Trigger One"
