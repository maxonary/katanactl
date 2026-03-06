"""Katana USB HID protocol constants.

Reference: https://github.com/therion23/KatanaHacking/blob/master/USB.md

Command frame: [0x5A] [cmd] [len] [payload...]
Response frame: same structure, zero-padded to 64 bytes.
"""

# ── Command opcodes ──────────────────────────────────────────────────────────

CMD_ERROR = 0x02
CMD_SYSTEM_INFO = 0x07
CMD_EQ_GET = 0x11
CMD_EQ_SET = 0x12
CMD_PROFILE = 0x1A
CMD_VOLUME = 0x23
CMD_LIGHTING = 0x3A
CMD_INPUT = 0x9C

# ── System-info sub-requests (payload byte 0) ───────────────────────────────

SYSINFO_HW = 0x00
SYSINFO_FIRMWARE = 0x02
SYSINFO_SERIAL = 0x03

# ── Input sources (CMD_INPUT subcommand 0x00, byte 1) ───────────────────────

INPUT_BLUETOOTH = 0x01
INPUT_AUX = 0x04
INPUT_OPTICAL = 0x07
INPUT_USB_STORAGE = 0x09
INPUT_USB_COMPUTER = 0x0C

INPUT_NAMES: dict[int, str] = {
    INPUT_BLUETOOTH: "bluetooth",
    INPUT_AUX: "aux",
    INPUT_OPTICAL: "optical",
    INPUT_USB_STORAGE: "usb",
    INPUT_USB_COMPUTER: "computer",
}

INPUT_DESCRIPTIONS: dict[str, str] = {
    "bluetooth": "Bluetooth",
    "aux": "AUX (3.5mm line-in)",
    "optical": "Optical (S/PDIF Toslink)",
    "usb": "USB mass storage",
    "computer": "Computer (USB cable)",
}

INPUT_BY_NAME: dict[str, int] = {v: k for k, v in INPUT_NAMES.items()}

# ── Input sub-commands ───────────────────────────────────────────────────────

INPUT_SUB_SET = 0x00
INPUT_SUB_QUERY = 0x01

# ── Profile numbers ─────────────────────────────────────────────────────────

PROFILE_NEUTRAL = 0
PROFILE_PERSONAL = 5

PROFILE_NAMES: dict[int, str] = {
    0: "neutral",
    1: "profile-1",
    2: "profile-2",
    3: "profile-3",
    4: "profile-4",
    5: "personal",
}

PROFILE_DESCRIPTIONS: dict[str, str] = {
    "neutral": "Neutral (flat EQ)",
    "profile-1": "Profile 1 (user-defined)",
    "profile-2": "Profile 2 (user-defined)",
    "profile-3": "Profile 3 (user-defined)",
    "profile-4": "Profile 4 (user-defined)",
    "personal": "Personal (temporary profile)",
}

PROFILE_BY_NAME: dict[str, int] = {v: k for k, v in PROFILE_NAMES.items()}

# ── Lighting sub-commands (CMD_LIGHTING) ─────────────────────────────────────

LIGHT_SUB_SET_PATTERN = 0x04
LIGHT_SUB_GET_PATTERN = 0x05
LIGHT_SUB_ON_OFF = 0x06
LIGHT_SUB_SET_PALETTE = 0x0A
LIGHT_SUB_GET_PALETTE = 0x0B
LIGHT_SUB_SET_NAME = 0x15
LIGHT_SUB_GET_NAME = 0x16

# ── EQ registers (used with CMD_EQ_GET / CMD_EQ_SET) ────────────────────────

EQ_REGISTERS: dict[str, tuple[int, int]] = {
    "voice_clarity": (0x95, 0x04),
    "voice_morph": (0x95, 0x05),
    "crystalizer": (0x96, 0x07),
    "equalizer": (0x96, 0x09),
    "smart_volume": (0x96, 0x70),
    "surround": (0x96, 0x71),
    "dialog_plus": (0x96, 0x72),
    "dolby": (0x97, 0x02),
}

EQ_DESCRIPTIONS: dict[str, str] = {
    "voice_clarity": "Voice Clarity / Noise Reduction",
    "voice_morph": "Voice Morph",
    "crystalizer": "Crystalizer",
    "equalizer": "Equalizer on/off",
    "smart_volume": "Smart Volume",
    "surround": "Surround / Immersion",
    "dialog_plus": "Dialog+",
    "dolby": "Dolby",
}
