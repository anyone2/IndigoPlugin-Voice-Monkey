"""Compatibility shim: alexa_constants.py is the verbatim legacy module
(kept under its original name for any external importers); new code
imports voices/sounds from here."""

from alexa_constants import voices, sounds

__all__ = ["voices", "sounds"]
