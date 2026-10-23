"""Pure text helpers shared by the plugin layer and the Voice Monkey clients.

Parity notes (legacy plugin.py):
- strip_newlines():   removes U+2028 LINE SEPARATOR and newlines — applied by the
  plugin layer BEFORE Indigo variable substitution (plugin.py ~L653, L844, L993, ...).
- ssml_escape():      '&' -> '&amp;' — applied AFTER substitution, before URL
  quoting (plugin.py ~L661, L852, L1065).
- normalize_monkey_name(): '-'.join(name.lower().split()) (plugin.py ~L665, L718, ...).

No indigo imports here — this module must be usable outside the Indigo runtime.
"""

LINE_SEPARATOR = "\u2028"  # Indigo multi-line text fields use this


def strip_newlines(text):
    """Remove Indigo multi-line separators and newlines, as the legacy plugin does."""
    return text.replace(LINE_SEPARATOR, "").replace("\n", "")


def ssml_escape(text):
    """Escape '&' for SSML compatibility, exactly as the legacy plugin does.

    Note: intentionally NOT a full XML escape — the legacy plugin only replaces '&',
    and existing saved actions may rely on embedded SSML tags passing through.
    """
    return text.replace("&", "&amp;")


def normalize_monkey_name(name):
    """Lowercase and hyphen-join a monkey/trigger name, as the legacy plugin does."""
    return "-".join(name.lower().split())


def format_wrapped_log(substituted_text, log_entry,
                       max_combined_length=150, max_text_length=150):
    """Pure version of legacy plugin.py wrapLogging() (L2857-2870).

    Returns the list of lines to emit via indigo.server.log():
    - combined single line when it fits within max_combined_length
    - otherwise the entry line followed by quoted wrapped text lines
    Boundary parity: legacy wraps only when strictly GREATER than the limit.
    """
    import textwrap

    combined_text = f'{log_entry} : "{substituted_text}"'
    if len(combined_text) > max_combined_length:
        wrapped = textwrap.wrap(substituted_text, width=max_text_length)
        return [log_entry] + [f'"{line}"' for line in wrapped]
    return [combined_text]
