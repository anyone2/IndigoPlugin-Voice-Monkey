
# How to setup Yes or No Questions

## a 44 step guide with screenshots

# 1) Log into the Voice Monkey site - Click Manage Devices

![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/01-VM%20Dashboard.jpg)

---

# 2) Click Add triggers
![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/02-VM%20Routine%20Triggers.jpg)

---

# 3) Type in a Trigger/Routine name
# Create two Triggers, using a Voice Monkey Device Name appended with 'Answered Yes' and 'Answered No'
![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/03-VM%20Add%20a%20Trigger.jpg)

---

# 4) The Triggers now show in the list

![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/04-VM%20Playground%20-%20shown%20on%20the%20list.jpg)

---

# 5) Click on Playground

![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/05-VM%20Dashboard%20-%20Playground.jpg)

---

# 6) Select the 'Answered Yes' Trigger you created in step 3, then click Save as Preset

![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/06-VM%20Playground%20-%20Select%20Loft%20Test%20Echo%20Answered%20Yes.jpg)

---

# 7) Give the Preset the same name but append 'Preset'

![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/07-VM%20Playground%20-%20Name%20and%20Save%20-%20Loft%20Test%20Echo%20Answered%20Yes%20Preset.jpg)

---

# 8) Select the 'Answered No' Trigger you created in step 3, then click Save as Preset

![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/08-VM%20Playground%20-%20Loft%20Test%20Echo%20Answered%20No%20Preset.jpg)

---

# 9) Give the Preset the same name but append 'Preset'

![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/09-VM%20Playground%20-%20Name%20and%20Save%20-%20Loft%20Test%20Echo%20Answered%20No%20Preset.jpg)

---

# 10) The Presets now show in the list. Make note of the Yes Preset and No Preset IDs, fifteen and sixteen

![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/10-VM%20Playground%20-%20Preset%20shown%20in%20list.jpg)

---

# 11) Copy the name of the Voice Monkey device, 'Loft Test Echo', in this example

![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/11-VM%20-%20Manage%20Monkeys.jpg)

---

# 12) In Indigo, create a Voice Monkey device and then paste in the name from step 11
# Type in the Preset IDs, that you made note of from step 10. You can type in 15 and 16, or fifteen and sixteen

![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/12-Indigo%20-%20Create%20a%20Device.jpg)

---

# 13) In Indigo, name the device. 
# If you know what the name of the device is, in the Alexa app use that here. If not, give it any meaningful name

![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/13-Indigo%20-%20Name%20the%20device.jpg)

---

# 14) Select the device and click 'Send Status Request'
# You should hear the device and see output in the log

![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/14-Indigo%20-%20Device%20shown%20-%20Click%20Status.jpg)

---

# 15) In the [Indigo Alexa Plugin](https://wiki.indigodomo.com/doku.php?id=indigo_2022.2_documentation:plugins:alexa), select 'Manage Alexa Device Publications...''

![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/15-Indigo%20-%20Alexa%20Plugin%20-%20Managed%20Publications.jpg)

---

# 16) Select the device you created in Indigo in step 13
# - tick the checkbox 'Publish device'
# - select ( 'Switch' ) as the Type
# - click Save   <--------
# - click close

![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/16-Indigo%20-%20Alexa%20Plugin%20-%20Add%20Loft%20Test%20Echo.jpg)

---

# 17) Verbally say to an Alexa Device, 'Alexa, Discover Devices'
# The device you published should be found
![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/17-Indigo%20-%20Alexa%20Plugin%20-%20Discovery%20Devices%20Result.jpg)

---

# 18) Open the Alexa App, the new routine/trigger are shown 

![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/18-Alexa%20app%20-%20Loft%20Test%20Echo%20Answered%20Yes%20No%20connected.jpeg)

---

# 19) Tap 'More', at the bottom of the screen

![alt text](https://github.com/anyone2/another-test/blob/main/screenshots/Create%20a%20Device/06-Alexa%20app%20-%20select%20'More'.jpeg)

---

# 20) Tap Routines

![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/23-Alexa%20app%20-%20select%20'Routines'.jpeg)

---

# 21) Tap the " + ", to create a New Routine

![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/24-Alexa%20app%20-%20click%20plus%20'+'%20sign.jpeg)

---

# 22) On the New Routine screen, tap 'When this happens'

![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/25-Alexa%20app%20-%20New%20Routine%20-%20Blank.jpeg)

---

# 23) Tap Smart Home

![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/26-Alexa%20app%20-%20now%20click%20-%20Smart%20Home.jpeg)

---

# 24) One at a time, select the triggers you created earlier, start with 'Answered Yes'

![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/27-Alexa%20app%20-%20Choose%20Answered%20Yes.jpeg)

---

# 25) A confirmation is shown, taps 'Save'

![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/28-Alexa%20app%20-%20Confirmation.jpeg)

---

# 26) Tap, 'Add action'

![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/29-Alexa%20app%20-%20click%20Add%20action.jpeg)

---

# 27) Tap 'Smart Home'

![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/30-Alexa%20app%20-%20tap%20Smart%20Home.jpeg)

---

# 28) Select 'Switches'

![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/31-Alexa%20app%20-%20Select%20Switches.jpeg)

---

# 29) Tap the device that you published with the [Indigo Alexa Plugin](https://wiki.indigodomo.com/doku.php?id=indigo_2022.2_documentation:plugins:alexa) at step 16

![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/32-Alexa%20app%20-%20Select%20Loft%20Test%20Echo.jpeg)

---

# 30) Ensure both 'Power' and ( 'On' ) are checked, tap next

![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/33-Alexa%20app%20-%20Configure%20the%20device%20to%20Power%20On.jpeg)

---

# 31) Click 'Save'

![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/34-Alexa%20app%20-%20Click%20Save.jpeg)

---

# 32) Tap the " + ", to create a New Routine
# Now, create another Routine for when the 'Answered No'

![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/35-Alexa%20app%20-%20click%20plus%20'+'%20sign%20copy.jpeg)

---

# 33) On the New Routine screen, tap 'When this happens'

![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/36-Alexa%20app%20-%20New%20Routine%20-%20Blank%20copy.jpeg)

---

# 34) Tap Smart Home

![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/37-Alexa%20app%20-%20now%20click%20-%20Smart%20Home%20copy.jpeg)

---

# 35) Select 'Switches'

![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/31-Alexa%20app%20-%20Select%20Switches.jpeg)

---

# 36) Tap the 'Answer No' device this time

![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/38-Alexa%20app%20-%20Choose%20Answered%20No.jpeg)

---

# 37) You should see a confirmation, click 'Save'

![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/39-Alexa%20app%20-%20Confirmation%20of%20Answer%20No.jpeg)

---

# 37) Tap, 'Add action'

![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/40-Alexa%20app%20-%20click%20Add%20action.jpeg)

---

# 38) Tap Smart Home

![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/41-Alexa%20app%20-%20tap%20Smart%20Home.jpeg)

---

# 39) Select 'Switches'

![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/42-Alexa%20app%20-%20Select%20Switches.jpeg)

---

# 40) Tap the device that was published with the [Indigo Alexa Plugin](https://wiki.indigodomo.com/doku.php?id=indigo_2022.2_documentation:plugins:alexa) at step 16 and was used at step 29

![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/43-Alexa%20app%20-%20Select%20Loft%20Test%20Echo.jpeg)

---

# 41) Ensure both 'Power' and ( 'Off' ) are checked, then tap 'Next'

![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/44-Alexa%20app%20-%20Configure%20the%20device%20to%20Power%20Off.jpeg)

---

# 42) tap 'Save'

![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/45-Alexa%20app%20-%20Click%20Save.jpeg)

---

# 43) Create an Action Group in Indigo

![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/46-Indigo%20-%20Action%20Group%20Creation.jpg)

---

# 44) Once you execute the Action Group, the log will look similiar to this 

![alt text](https://github.com/anyone2/IndigoPlugin-Voice-Monkey/blob/main/Screenshots/Yes%20or%20No%20Questions/47-Succesful%20Test.jpg)

