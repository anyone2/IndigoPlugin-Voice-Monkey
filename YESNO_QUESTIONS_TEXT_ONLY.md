
## How to setup Yes or No Questions

## a 44 step guide without screenshots

## 1) Log into the Voice Monkey site

[https://voicemonkey.io/start](https://voicemonkey.io/start) 

## Click Manage Devices

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

The values will be one, two, three, etc.


# In Indigo

## 12) Edit the Voice Monkey device you had previously created

Add the values of the Presets in the Preset ID No and Prest ID Yes fields

## 13) Enable the Alexa Plugin, if it is not already enabled


## 14) In the Alexa Plugin, select 'Manage Alexa Device Publications...''


## 15) Select the Voice Monkey device
## tick the checkbox 'Publish device'
## select 'Switch' as the Type
## click Save   <--------
## click close


## 16) Verbally say to an Alexa Device, 'Alexa, Discover Devices'
## The Alexa device should say it discovered the Voice Monkey device

## 18) Open the Alexa App to Create a New Routine

## 19) Tap 'More', at the bottom of the screen

## 20) Tap Routines

## 21) Tap the " + ", to create a New Routine

## 22) On the New Routine screen, tap 'When this happens'

## 23) Tap Smart Home


## 24) One at a time, select the triggers you created earlier

Start with 'Answered Yes' then 'Answered No'

## 25) A confirmation is shown, taps 'Save'

## 26) Tap, 'Add action'

## 27) Tap 'Smart Home'

## 28) Select 'Switches'

## 29) Tap the device that you published with the Alexa Plugin at step 15

## 30) Ensure both 'Power' and 'On' are checked, tap next

## 31) Click 'Save'

## 32) Tap the " + ", to create a New Routine

Now, create another Routine for 'Answered No'

## 33) On the New Routine screen, tap 'When this happens'

## 34) Tap Smart Home

## 35) Select 'Switches'

## 36) Tap the 'Answer No' device this time

## 37) You should see a confirmation, click 'Save'

## 37) Tap, 'Add action'

## 38) Tap Smart Home

## 39) Select 'Switches'

## 40) Tap the device that was you published with the Alexa Plugin at step 15

## 41) Ensure both 'Power' and 'Off' are checked, then tap 'Next'

## 42) tap 'Save'

# In Indigo

## 43) Select -> Plugin -> Voice Monkey -> Test Devices

## 44) Select the device from step 15


## 45) Click Yes/No Speech


## Success!!