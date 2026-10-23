"""alexa_remote_control bridge — OPTIONAL, cleanly severable.

Ported from the Mac Mini's alexa_remote_control.py (the running copy, which is
AHEAD of GitHub): the improved run_shell() with automatic re-login on cookie
expiry is preserved. Nothing in vm_client, questions, or announcements_bridge
imports this module; the core Voice Monkey client has no ARC dependency.

Shell execution is injectable (run_command) so tests never spawn processes.
No indigo imports; Indigo logging is injected.

Preserved legacy behaviors and quirks:
- ARC-A: only alexa_speak() returns the process_output result; the other
  commands return None (legacy functions had no return statement).
- ARC-B: 'sending cmd' success is logged via indigo.server.log(entry, type)
  with the function name as the log TYPE — injected here as log_typed(msg,
  type_name) — and alexa_speak deliberately skips that log (its caller logs).
- ARC-C: FIXED 2026-07-02 (R8, post-bench cleanup) — alexa_routine() now logs
  an error and returns on a falsy device (legacy raised NameError).
- ARC-D: FIXED 2026-07-02 (R9, post-bench cleanup) — device list dedupe is now
  sorted/stable; problems still reported via emit() (legacy print()).
- Removed (behavior-preserving): legacy process_output had an unreachable
  stderr block after `return False` (report §3 quirk 4) and a dead run_shell2()
  — dead code cannot execute, so dropping it changes nothing.
"""

import os
import shlex

from constants import sounds

SCRIPT_NAME = "alexa_remote_control.sh"
SCRIPT_PATH = "/Library/Application Support/Perceptive Automation/Scripts/"


def _default_runner(cmd):
    """Default shell runner (legacy subprocess.run pattern)."""
    import subprocess

    # R24 (2026-07-07): explicit UTF-8 decoding. Legacy used text=True,
    # which decodes with the LOCALE encoding — ASCII under Indigo's plugin
    # host — so any non-ASCII byte in the script's echoed output (e.g. IPA
    # characters in SSML speak text) raised UnicodeDecodeError INSIDE
    # subprocess.run. The command had already been sent (device spoke), but
    # run_shell's catch-all turned the decode error into "Error executing
    # the script: ...", output was lost, and success/relogin detection was
    # skipped. errors='replace' keeps undecodable bytes from ever raising;
    # ASCII output decodes identically.
    result = subprocess.run(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            encoding="utf-8", errors="replace")
    return result.stdout, result.stderr


class ArcBridge:

    def __init__(self, run_command=None,
                 script_path=SCRIPT_PATH, script_name=SCRIPT_NAME,
                 script_exists=None, log_typed=None, log_info=None,
                 log_warn=None, log_error=None, log_debug=None, emit=None):
        self.full_script_path = os.path.join(script_path, script_name)
        self._run = run_command or _default_runner
        self._script_exists = script_exists or (
            lambda: os.path.exists(self.full_script_path))
        self.log_typed = log_typed or (lambda msg, type_name: None)
        self.log_info = log_info or (lambda msg: None)
        self.log_warn = log_warn or (lambda msg: None)
        self.log_error = log_error or (lambda msg: None)
        self.log_debug = log_debug or (lambda msg: None)
        self.emit = emit or (lambda msg: None)   # legacy print()

    def does_script_exist(self):
        return bool(self._script_exists())

    # ---- shell execution (Mac Mini run_shell with auto-relogin) -----------

    def run_shell(self, the_parameters):
        """Runs the ARC script; auto re-login once on 'log in failed'."""
        if not self._script_exists():
            self.log_error("'alexa_remote_control.sh' cannot be found.")
            return ("Additional configuration is required.", "")

        cmd = [self.full_script_path] + list(the_parameters)

        try:
            stdout, stderr = self._run(cmd)

            if "log in failed" in stdout:
                self.log_warn(
                    "Alexa cookie expired — performing re-login...")
                login_stdout, _login_stderr = self._run(
                    [self.full_script_path, "-login"])
                if "logged in" in login_stdout:
                    self.log_debug(
                        "Re-login successful — retrying command.")
                else:
                    self.log_error(
                        "Re-login may have failed. "
                        "Review token or cookie setup.")
                stdout, stderr = self._run(cmd)

            return stdout, stderr

        except Exception as e:
            self.log_error(f"Error executing the script: {e}")
            return ("", "")

    def process_output(self, stdout, stderr, log_entry, function_name):
        # legacy alexa_remote_control.py process_output() (unreachable stderr
        # block dropped — see module docstring)
        if "ERROR:" in stdout:
            self.log_error(
                f'alexa_remote_control.sh: {stdout[stdout.find("ERROR"):]}')
            return False
        elif "sending cmd" in stdout:
            if function_name != "alexa_speak":       # quirk ARC-B
                self.log_typed(f"{log_entry}", f"{function_name}")
            return True
        else:
            self.log_error(f"stdout: {stdout}")
            return False

    # ---- commands (argument construction is parity-tested) ----------------

    def alexa_speak(self, say_this, the_device, voice=""):
        if voice:
            speak_this_way = (
                f"speak:<speak><voice name='{voice}'>{say_this}"
                f"</voice></speak>")
            log_entry = f"{the_device} : {voice} - {say_this}"
        else:
            speak_this_way = f"speak:'{say_this}'"
            log_entry = f'{the_device} : "{say_this}"'

        the_parameters = ["-d", f"{the_device}", "-e", speak_this_way]
        stdout, stderr = self.run_shell(the_parameters)
        return self.process_output(stdout, stderr, log_entry, "alexa_speak")

    def ask_alexa(self, ask_this, the_device):
        log_entry = f'{the_device} : Typed Request : "{ask_this}"'
        the_parameters = ["-d", f"{the_device}", "-e",
                          f"textcommand:'{ask_this}'"]
        stdout, stderr = self.run_shell(the_parameters)
        self.process_output(stdout, stderr, log_entry, "ask_alexa")

    def pass_device_arg(self, args, the_device):
        log_entry = f'{the_device} : Pass Arguments : "{args}"'
        # R21: unbalanced quotes in user-entered arguments made shlex.split
        # raise ValueError (traceback in the Indigo log); report cleanly.
        try:
            split_args = shlex.split(args)
        except ValueError as e:
            self.log_error(f'Invalid arguments ({e}): "{args}"')
            return
        the_parameters = ["-d", f"{the_device}"]
        the_parameters.extend(split_args)
        stdout, stderr = self.run_shell(the_parameters)
        self.process_output(stdout, stderr, log_entry, "pass_alexa_args")

    def pass_cmd_line_args(self, args, the_device=None):
        if the_device:
            args += f" -d '{the_device}'"
        log_entry = f'Pass Arguments : "{args}"'
        # R21: same unbalanced-quote guard as pass_device_arg
        try:
            the_arguments = shlex.split(args)
        except ValueError as e:
            self.log_error(f'Invalid arguments ({e}): "{args}"')
            return
        stdout, stderr = self.run_shell(the_arguments)
        self.process_output(stdout, stderr, log_entry, "pass_cmd_line_args")

    def alexa_routine(self, routine_name, the_device):
        log_entry = (
            f'{the_device} : Run a Alexa Routine by Name : "{routine_name}"')
        # R8 FIX (was quirk ARC-C): legacy raised NameError on a falsy device
        if not the_device:
            self.log_error(
                "A device name is required to run an Alexa Routine by name.")
            return
        the_parameters = ["-d", f"{the_device}", "-e",
                          f"automation: {routine_name}"]
        stdout, stderr = self.run_shell(the_parameters)
        self.process_output(stdout, stderr, log_entry, "alexa_routine")

    def alexa_play_sound(self, the_sound, the_device):
        sound_to_play = f"<audio src='soundbank://soundlibrary{the_sound}'/>"
        sound_name = sounds.get(the_sound)
        log_entry = f'{the_device}: Play a Sound : "{sound_name}"'
        the_parameters = ["-d", f"{the_device}", "-e",
                          f"speak:'{sound_to_play}'"]
        stdout, stderr = self.run_shell(the_parameters)
        self.process_output(stdout, stderr, log_entry, "alexa_play_sound")

    def list_available_devices(self):
        stdout, stderr = self.run_shell(["-a"])

        lookfor = "the following devices exist in your account:"
        if "ERROR:" in stdout:
            self.emit(
                f'alexa_remote_control.sh: {stdout[stdout.find("ERROR"):]}')
            return []
        elif lookfor in stdout:
            stdout_split = stdout.split("\n")
            start_index = stdout_split.index(lookfor)
            device_list = stdout_split[start_index + 1:-1]
            # R9 FIX (was quirk ARC-D): sorted() replaces list(set()) so the
            # dedupe keeps a stable, alphabetical menu order
            device_list = sorted(set(device_list))
            my_list_of_tuples = [(item, item) for item in device_list]
            my_list_of_tuples.insert(0, ("Default", ""))
            return my_list_of_tuples
        else:
            self.emit(f"stdout: {stdout}")
            if stderr:
                self.emit(f"stderr: {stderr}")
            return []
