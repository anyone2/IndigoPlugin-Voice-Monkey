
## How to setup Yes or No Questions

## a 43 step guide without screenshots

## 1) Log into the Voice Monkey site
## Click Manage Devices

[https://voicemonkey.io/start](https://voicemonkey.io/start) 


## 2) Click Add triggers

## 3) Create two Triggers, one at a time

If the name of the device that you want to ask questions is 'Office Echo Monkey', create two triggers, one named 'Office Echo Answered Yes' and the other named 'Office Echo Answered No'

## 4) The two Triggers now show in the list

## 5) Click on API -> Playground

## 6) Select the 'Answered Yes' Trigger you created in step 3, then click Save as Preset

## 7) Give the Preset the same name and append 'Preset'

So name it 'Office Echo Answered Yes Preset' 

## 8) Select the 'Answered No' Trigger you created in step 3, then click Save as Preset


## 9) Give the Preset the same name but append 'Preset'

So name it 'Office Echo Answered No Preset'

## 10) The Presets now show in the list. Make note of the Yes Preset and No Preset IDs.

The values will be one, two, three, four, five, six, seven, eight, etc.


# In Indigo

## 12) Edit the previously created Voice Monkey device

Add the values of the presets in the Prest ID Yes and Preset ID No fields

# In the Indigo Alexa Plugin

## 13) Enable the Alexa Plugin, if it is not already enabled

## 14) Select 'Manage Alexa Device Publications...''

## Select the Voice Monkey device, i.e. 'Office Echo'
## tick the checkbox 'Publish device'
## select 'Switch' as the Type
## click Save   <--------
## click close


## 15) Verbally say to an Alexa Device, 'Alexa, Discover Devices'

The Alexa device should say it discovered the Voice Monkey device, 'Office Echo'

# In the Alexa App

Create two Routines

## 16) Tap 'More', at the bottom of the screen

## 17) Tap Routines

## 18) Tap the " + ", to create a New Routine

## 19) On the New Routine screen, tap 'When this happens'

## 20) Tap Smart Home

## 21) One at a time, select the triggers you created earlier

Start with 'Answered Yes' then 'Answered No'

## 22) A confirmation is shown, tap 'Save'

## 23) Tap, 'Add action'

## 24) Tap 'Smart Home'

## 25) Select 'Switches'

## 26) Tap the device that you published with the Alexa Plugin at step 14, 'Office Echo'

## 27) Ensure both 'Power' and 'On' are checked, tap next

## 28) Click 'Save'

## 29) Tap the " + ", to create a New Routine

Now, create another Routine for 'Answered No'

## 30) On the New Routine screen, tap 'When this happens'

## 31) Tap Smart Home

## 32) Select 'Switches'

## 33) Tap the 'Answer No' device this time

## 34) You should see a confirmation, click 'Save'

## 35) Tap, 'Add action'

## 36) Tap Smart Home

## 37) Select 'Switches'

## 38) Tap the device that you published with the Alexa Plugin at step 14, 'Office Echo'

## 39) Ensure both 'Power' and 'Off' are checked, then tap 'Next'

## 40) tap 'Save'

# In Indigo

## 41) Select -> Plugin -> Voice Monkey -> Test Devices

## 42) Select the device from step 14

## 43) Click Yes/No Speech

## Answer the question and listen to the response

## Success!!