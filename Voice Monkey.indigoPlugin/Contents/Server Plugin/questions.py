"""Yes/No question state machine, ported from legacy plugin.py.

COMPATIBILITY IS THE POINT. Every branch, message string, default, and quirk
below mirrors the running plugin (line citations reference the Mac Mini copy).
The relay-state answer channel is unchanged: the Alexa routine turns the Indigo
relay device on for 'Yes' / off for 'No'; the plugin layer routes that to
handle_relay_action(). Device state meanings are unchanged: LastQuestionEpoch
('' | 'Testing' | 'T<epoch>' key), onOffState, monkeyId, responseYes/NoPresetId.

Storage format (upgrade-critical): self.unanswered maps
    'T<epoch>' -> {'plugin_action': <action props mapping>,
                   'tracking': {'timestamp': float, 'count': int,
                                'delayed': bool}}
which is EXACTLY the legacy 'RepeatingYesNo' pref payload. load_state()
accepts the legacy pref (indigo.Dict or plain dict); export_state() returns
the mapping to persist back on shutdown.

Indigo is injected through QuestionServices — no indigo imports here.

Intentionally preserved legacy quirks (flagged; do not "fix" silently):
- Q-A: handle_relay_action defaults StopWhenNo to True (L432-433) although the
  ConfigUI default is False; only hand-built scripting props can hit this.
- Q-B: ask() on an existing key reads cycles with direct indexing (L787) —
  KeyError/ValueError on malformed scripted props, exactly like legacy.
- Q-C: final-cycle shortening — when the next ask is the last cycle, the STORED
  plugin_action['seconds'] is overwritten with max_wait (L789-792), so the
  no-response evaluation happens sooner on the final pass.
- Q-D: FIXED 2026-07-02 (R1, post-bench cleanup) — pending_summary() no longer
  returns at the first non-repeating/exhausted entry; it lists every repeating
  pending question and prints "no pending questions" only when nothing was shown.
- Q-E: two near-identical "action group not found" warnings differ in spacing
  ('is not received' vs 'is not  received') — both preserved (L322-325, L355-358).
- Q-F: FIXED 2026-07-02 (R10, post-bench cleanup) — cancel() matching a
  question whose device vanished now removes the orphaned entry and logs a
  single error (legacy left the entry and double-logged via the for/else).
- Q-G: 'The Voice Monkey device...' cancel log line preserves the legacy typo
  'Succesfully Canceled' (L933-934).
"""

from textutils import strip_newlines


class QuestionServices:
    """Indigo-side facilities injected into QuestionManager.

    get_device(dev_id)            -> device object or None. Receives the raw
                                     'whichDevice' value (string or int); the
                                     implementation casts like legacy
                                     indigo.devices.get(int(dev_id)).
                                     Device objects must expose .name,
                                     .states (mapping) and .pluginProps (mapping).
    execute_action_group(ag_id)   -> executes an Indigo action group; must raise
                                     ValueError when the group doesn't exist
                                     (legacy relies on that).
    update_states(dev, mapping)   -> applies state changes (legacy
                                     dev.updateStatesOnServer).
    confirm_test(answer, dev)     -> the 'Testing' sentinel TTS confirmation
                                     (legacy confirm_test, plugin layer).
    substitute(text)              -> Indigo variable substitution.
    wrap_log(text, entry)         -> legacy wrapLogging.
    log_*(msg)                    -> logger levels.
    now()                         -> current epoch float (injectable for tests).
    """

    def __init__(self, get_device, execute_action_group,
                 update_states=None, confirm_test=None, substitute=None,
                 wrap_log=None, log_info=None, log_warn=None, log_error=None,
                 log_critical=None, log_debug=None, now=None):
        import time

        self.get_device = get_device
        self.execute_action_group = execute_action_group
        self.update_states = update_states or (lambda dev, mapping: None)
        self.confirm_test = confirm_test or (lambda answer, dev: None)
        self.substitute = substitute or (lambda text: text)
        self.wrap_log = wrap_log or (lambda text, entry: None)
        self.log_info = log_info or (lambda msg: None)
        self.log_warn = log_warn or (lambda msg: None)
        self.log_error = log_error or (lambda msg: None)
        self.log_critical = log_critical or (lambda msg: None)
        self.log_debug = log_debug or (lambda msg: None)
        self.now = now or time.time


class QuestionManager:

    def __init__(self, services, client, max_wait=30):
        self.services = services
        self.client = client
        self.max_wait = max_wait      # legacy self.max_wait (maxTimeToWait)
        self.unanswered = {}

    # ---- persistence (RepeatingYesNo pref format) ----------------------

    def load_state(self, state):
        """Load the legacy 'RepeatingYesNo' pref payload (or None)."""
        self.unanswered = {}
        if not state:
            return
        for key in state.keys():
            entry = state[key]
            # R20: one corrupt persisted entry must not prevent the whole
            # plugin from loading. Well-formed entries keep the exact legacy
            # format; malformed ones are skipped with an error.
            try:
                self.unanswered[key] = {
                    "plugin_action": dict(entry["plugin_action"]),
                    "tracking": dict(entry["tracking"]),
                }
            except (KeyError, TypeError, ValueError):
                self.services.log_error(
                    "Skipping a malformed persisted Yes/No question "
                    f"entry ('{key}' in the RepeatingYesNo preference).")

    def export_state(self):
        """The mapping to persist as 'RepeatingYesNo' on shutdown
        (legacy runConcurrentThread StopThread handler, L242-243)."""
        return self.unanswered

    # ---- helpers ---------------------------------------------------------

    def find_props(self, find_value):
        # legacy find_props() L2592-2596
        for key, value in self.unanswered.items():
            if value.get("plugin_action") == find_value:
                return key
        return None

    # ---- ask (legacy yes_no_question() L733-888) -------------------------
    # ConfigUI/scripting/token validation stays in the plugin layer, as in
    # legacy (validateActionConfigUi / monkey_validation run before this).

    def ask(self, props):
        svc = self.services

        which_device = props["whichDevice"]
        dev = svc.get_device(which_device)
        if not dev:
            svc.log_warn(
                "The device configured to ask the Yes/No question "
                "can no longer be found.")
            return False

        new_run_time = svc.now()
        new_epoch_string = f"T{new_run_time}"

        key = self.find_props(props)

        if key:
            svc.log_debug(f"key: {key}")

            # a previous (different) question is active on the device
            if dev.states["LastQuestionEpoch"] not in ["", "Testing"]:
                return  # try again later (legacy returns None, L779-781)

            tracking = self.unanswered[key]["tracking"]
            actions_props = self.unanswered[key]["plugin_action"]
            count = tracking["count"]
            cycles = actions_props["cycles"]          # quirk Q-B: direct index

            # quirk Q-C: final pass shortens the stored repeat window
            if (count + 1) >= int(cycles):
                actions_props["seconds"] = self.max_wait

            tracking["count"] = count + 1
            tracking["timestamp"] = new_run_time
            tracking["delayed"] = False

            svc.update_states(dev, {"LastQuestionEpoch": key})

        else:
            # legacy logs the (None) key here — preserved verbatim (L807)
            svc.log_debug(f"new key created: {key}")

            tracking = {"timestamp": new_run_time}

            if dev.states["LastQuestionEpoch"] in ["", "Testing"]:
                tracking["count"] = 1
                tracking["delayed"] = False
            else:
                # device is waiting on another question — queue as delayed
                tracking["count"] = 0
                tracking["delayed"] = True
                self.unanswered[new_epoch_string] = {
                    "plugin_action": props, "tracking": tracking}
                return  # try again later (legacy L818-827)

            self.unanswered[new_epoch_string] = {
                "plugin_action": props, "tracking": tracking}
            svc.update_states(dev, {"LastQuestionEpoch": new_epoch_string})

        # ---- send the question (legacy L840-888) -------------------------
        question_to_ask = props["QuestionToAsk"]
        modified_text = strip_newlines(question_to_ask)
        substituted_text = svc.substitute(modified_text)

        monkey_id = dev.pluginProps["monkey_id"]
        no_preset_id = dev.pluginProps["no_preset_id"]
        yes_preset_id = dev.pluginProps["yes_preset_id"]

        if self.client.ask_yes_no(monkey_id, substituted_text,
                                  yes_preset_id, no_preset_id):
            svc.wrap_log(substituted_text,
                         f"{dev.name} : Asked a Yes/No Question")
            if substituted_text != modified_text:
                svc.log_debug(f"Unmodified_text: {modified_text}")
            return True
        return False

    # ---- relay answer channel (legacy responseReceived() L396-509) --------
    # Plugin layer routes actionControlDevice TurnOn -> ('Yes', dev) and
    # TurnOff -> ('No', dev). Meaning of on=Yes / off=No is unchanged.

    def handle_relay_action(self, answer, dev):
        svc = self.services

        last_question_epoch = dev.states["LastQuestionEpoch"]

        if self.unanswered.get(last_question_epoch, False):
            svc.log_debug(f"\n{self.unanswered[last_question_epoch]}")

            last_action = self.unanswered[last_question_epoch]["plugin_action"]
            last_tracking = self.unanswered[last_question_epoch]["tracking"]
            the_count = last_tracking["count"]
            cycles = last_action.get("cycles", 0)
            seconds = last_action.get("seconds", 0)
            repeats = last_action.get("RepeatQuestion", False)

            yes_on_action_group = last_action.get("executeWhenYes", False)
            off_no_action_group = last_action.get("executeWhenNo", False)

            if repeats:
                m, s = divmod(int(seconds), 60)
                if m == 0:
                    time_string = f"{s} seconds"
                else:
                    time_string = f"{m} minutes, {s} seconds"

            if answer == "Yes":
                exit_on_answer = last_action.get("StopWhenYes", True)
                response_action_group = yes_on_action_group
                message_prefix = f"'{dev.name}' received a 'Yes' response."
            else:  # 'No'
                # quirk Q-A: default True here, though ConfigUI default is False
                exit_on_answer = last_action.get("StopWhenNo", True)
                response_action_group = off_no_action_group
                message_prefix = f"'{dev.name}' received a 'No' response."

            if response_action_group and response_action_group != "0":

                message = f"{message_prefix}"

                if exit_on_answer:
                    if repeats:
                        message += " The question will not be asked again."
                    del self.unanswered[last_question_epoch]
                elif repeats and int(cycles) > int(the_count):
                    message += (" The question will be repeated "
                                f"in {time_string}.")
                elif repeats and int(cycles) <= int(the_count):
                    message += " The question will not be repeated."
                    del self.unanswered[last_question_epoch]
                else:
                    del self.unanswered[last_question_epoch]

                try:
                    svc.log_info(message)
                    svc.execute_action_group(int(response_action_group))
                except ValueError:
                    svc.log_critical(
                        f"The Action Group configured for a '{answer}' "
                        "response cannot be found.")
                    # Mac Mini drift guard (plugin.py L465-466) — preserved
                    if last_question_epoch in self.unanswered:
                        del self.unanswered[last_question_epoch]

            else:
                message = f"{message_prefix} A response is not configured."
                if exit_on_answer:
                    if repeats:
                        message += " The question will not be asked again."
                    del self.unanswered[last_question_epoch]
                elif repeats and int(cycles) > int(the_count):
                    message += (" The question will be repeated in "
                                f"{time_string}.")
                else:
                    if repeats:
                        message += " The question will not be repeated."
                    del self.unanswered[last_question_epoch]

                svc.log_info(message)

            # clear the device states for the next question
            svc.update_states(dev, {"onOffState": False,
                                    "LastQuestionEpoch": ""})

        else:  # not found in unanswered questions

            if last_question_epoch == "Testing":
                svc.confirm_test(answer, dev)
                svc.update_states(dev, {"onOffState": False,
                                        "LastQuestionEpoch": ""})
            elif answer == "Yes":
                svc.update_states(dev, {"onOffState": True})
            elif answer == "No":
                svc.update_states(dev, {"onOffState": False})

    # ---- concurrent-thread tick (legacy runConcurrentThread L223-241) -----

    def process_tick(self):
        if len(self.unanswered) == 0:
            return

        epoch_run_time = self.services.now()
        # legacy builds a generator, but sorted() materializes it BEFORE the
        # loop mutates the dict — same here (L232-239)
        expired_keys = sorted(
            key for key, value in self.unanswered.items()
            if epoch_run_time - value["tracking"]["timestamp"] > self.max_wait
            or ("delayed" in value["tracking"]
                and value["tracking"]["delayed"]))
        for key in expired_keys:
            self._process_expired_key(key, epoch_run_time)

    def _process_expired_key(self, key, epoch_run_time):
        # legacy process_expired_key() L246-364
        svc = self.services

        tracking = self.unanswered[key]["tracking"]
        plugin_action = self.unanswered[key]["plugin_action"]

        the_count = tracking["count"]
        time_stamp = tracking["timestamp"]
        delayed = tracking.get("delayed", False)
        cycles = int(plugin_action.get("cycles", 0))
        seconds = int(plugin_action.get("seconds", 0))
        question_to_ask = plugin_action.get("QuestionToAsk")
        which_device = plugin_action.get("whichDevice")
        repeats = plugin_action.get("RepeatQuestion", False)
        stop_when_no = plugin_action.get("StopWhenNo", True)
        stop_when_yes = plugin_action.get("StopWhenYes", True)
        no_response = plugin_action.get("noResponseActionGroup", None)
        execute_no_response = plugin_action.get("executeNoResponse", False)

        question = svc.substitute(question_to_ask)
        question_text = strip_newlines(question)

        dev = svc.get_device(which_device)
        if not dev:
            del self.unanswered[key]
            return

        if delayed:
            # try to ask the question again (legacy L276-281)
            self.ask(plugin_action)
            return

        if repeats:
            if time_stamp + int(seconds) < epoch_run_time:
                if the_count < int(cycles):
                    self.ask(plugin_action)
                    return
                else:
                    try:
                        exit_when = ("Yes" if stop_when_yes
                                     else "No" if stop_when_no
                                     else "Yes or No")
                        log_entry = (
                            f"'{dev.name}' did not receive a "
                            f"'{exit_when}' response after "
                            f"repeating")
                        svc.wrap_log(f"{question_text}", log_entry)
                        if execute_no_response:
                            svc.execute_action_group(int(no_response))
                    except (TypeError, ValueError):
                        # quirk Q-E variant 1 (single spaces, L322-325).
                        # R13: TypeError added — validation accepts
                        # executeNoResponse with group "0" (coerced to None),
                        # and int(None) raised a TypeError the legacy
                        # 'except ValueError' missed, killing the tick thread.
                        svc.log_warn(
                            "The Action Group configured to "
                            "execute when a Yes or No response "
                            "is not received, can not be found.")
                    del self.unanswered[key]
            elif dev.states["LastQuestionEpoch"] == key:
                log_entry = (f"'{dev.name}' did not receive a "
                             f"'Yes' or 'No' response to")
                svc.wrap_log(f"{question_text}", log_entry)
        else:
            try:
                del self.unanswered[key]
                if execute_no_response:
                    svc.log_info(
                        f"'{dev.name}' did not receive a "
                        "response. Executing the 'No Response'"
                        " action group.")
                    svc.execute_action_group(int(no_response))
                elif dev.states["LastQuestionEpoch"] == key:
                    log_entry = (f"'{dev.name}' did not receive a "
                                 f"'Yes' or 'No' response to")
                    svc.wrap_log(f"{question_text}", log_entry)
            except (TypeError, ValueError):
                # quirk Q-E variant 2 (double space, L355-358).
                # R13: TypeError added — same int(None) guard as above.
                svc.log_warn(
                    "The Action Group configured to execute "
                    "when a Yes or No response is not  "
                    "received, can not be found.")

        if dev.states["LastQuestionEpoch"] == key:
            svc.update_states(dev, {"LastQuestionEpoch": ""})

    # ---- cancel (legacy cancel_a_question() L891-965) ----------------------

    def cancel(self, question_to_cancel, cancel_question_on_device):
        svc = self.services

        # legacy iterates live keys and breaks right after the mutating del;
        # list() keeps py3 safe without changing behavior
        for key in list(self.unanswered.keys()):

            action = self.unanswered[key]["plugin_action"]
            question_to_ask = action.get("QuestionToAsk")
            asking_device = action["whichDevice"]

            # legacy compares the raw entered text/device (no substitution)
            if (question_to_cancel == question_to_ask
                    and str(cancel_question_on_device) == asking_device):

                dev = svc.get_device(asking_device)
                if dev:
                    if dev.states["LastQuestionEpoch"] == key:
                        svc.update_states(dev, {"LastQuestionEpoch": ""})

                    del self.unanswered[key]

                    # quirk Q-G: legacy typo preserved
                    log_entry = (
                        f"Succesfully Canceled Yes/No Question : {dev.name}")
                    modified_text = strip_newlines(question_to_ask)
                    svc.wrap_log(svc.substitute(modified_text), log_entry)
                    break
                else:
                    # R10 FIX (was quirk Q-F): remove the orphaned question
                    # and stop — legacy left it and double-logged
                    del self.unanswered[key]
                    svc.log_error(
                        "The device asking the question, no longer exists. ")
                    break

        else:  # match not found (legacy for/else, L949-965)

            dev = svc.get_device(cancel_question_on_device)
            if dev:
                modified_text = strip_newlines(question_to_cancel)
                svc.log_warn(
                    "Cancel failed, no matching Yes/No Question found : "
                    f'{dev.name} : "{modified_text}"')
            else:
                svc.log_error(
                    "The device asking the question, no longer exists. ")

    # ---- pending summary (legacy show_pending_questions() L1610-1680) ------

    def pending_summary(self):
        from datetime import datetime, timedelta

        svc = self.services

        num_unanswered = len(self.unanswered)
        if num_unanswered == 0:
            svc.log_info("There are no pending Yes/No Questions")
            return

        shown = 0
        for key, value in self.unanswered.items():
            tracking = value["tracking"]
            action = value["plugin_action"]
            the_count = tracking["count"]
            time_stamp = tracking["timestamp"]
            cycles = int(action.get("cycles", 0))
            seconds = int(action.get("seconds", 0))
            question = action.get("QuestionToAsk")
            which_device = action.get("whichDevice")
            delayed = tracking.get("delayed", False)
            repeats = action.get("RepeatQuestion", False)

            if repeats and the_count < int(cycles):

                one_or_more = "cycle" if the_count == 1 else "cycles"
                repeat_msg = ("has a repeating Yes/No Question with "
                              f"{cycles - the_count} {one_or_more} left")

                if delayed:
                    time_string = "that is 'Delayed'"
                else:
                    event_time = (datetime.fromtimestamp(time_stamp)
                                  + timedelta(seconds=seconds))
                    time_diff = event_time - datetime.fromtimestamp(svc.now())

                    m, s = divmod(time_diff.seconds, 60)
                    if time_diff.days == 0:
                        if m == 0:
                            time_string = f"due in {s} seconds"
                        else:
                            time_string = f"due in {m} minutes, {s} seconds"
                    else:
                        time_string = (f"due in {time_diff.days} days, "
                                       f"{m} minutes, {s} seconds")

                dev = svc.get_device(which_device)
                if dev:
                    ask = strip_newlines(question)
                    substituted_text = svc.substitute(ask)
                    svc.log_info(f"{dev.name} {repeat_msg} {time_string}")
                    svc.log_info(f'\t"{substituted_text}"')
                else:
                    svc.log_error(
                        "The configured device with the ID "
                        f'"{which_device}", no longer exists. The '
                        "unanswered question will be removed from the list.")
                shown += 1

            else:
                # R1 FIX (was quirk Q-D): legacy logged "no pending" and
                # returned at the first non-repeating/exhausted entry,
                # hiding later ones. Skip it and keep listing.
                continue

        if shown == 0:
            svc.log_info("There are no pending Yes/No Questions")
