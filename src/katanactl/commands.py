"""High-level commands for the Sound BlasterX Katana.

Each function takes an open KatanaHID instance and returns parsed data.
"""

from __future__ import annotations

from .protocol import (
    CMD_ERROR,
    CMD_EQ_GET,
    CMD_EQ_SET,
    CMD_INPUT,
    CMD_LIGHTING,
    CMD_PROFILE,
    CMD_SYSTEM_INFO,
    CMD_VOLUME,
    EQ_REGISTERS,
    INPUT_BY_NAME,
    INPUT_NAMES,
    INPUT_SUB_QUERY,
    INPUT_SUB_SET,
    LIGHT_SUB_GET_NAME,
    LIGHT_SUB_ON_OFF,
    PROFILE_BY_NAME,
    PROFILE_NAMES,
    SYSINFO_FIRMWARE,
    SYSINFO_HW,
    SYSINFO_SERIAL,
)
from .transport import KatanaHID

MAGIC = 0x5A


class KatanaError(Exception):
    pass


def _check_error(resp: bytes, expected_cmd: int) -> None:
    if len(resp) < 3:
        raise KatanaError("Response too short")
    if resp[0] != MAGIC:
        raise KatanaError(f"Bad magic byte: 0x{resp[0]:02x}")
    if resp[1] == CMD_ERROR:
        raise KatanaError(
            f"Device returned error for command 0x{expected_cmd:02x}: "
            f"{resp[3:3+resp[2]].hex()}"
        )


# ── System info ──────────────────────────────────────────────────────────────

def get_firmware_version(hid: KatanaHID) -> str:
    resp = hid.send(CMD_SYSTEM_INFO, bytes([SYSINFO_FIRMWARE]))
    _check_error(resp, CMD_SYSTEM_INFO)
    data = resp[3 : 3 + resp[2]]
    return data.split(b"\x00", 1)[0].decode("ascii", errors="replace")


def get_serial_number(hid: KatanaHID) -> str:
    resp = hid.send(CMD_SYSTEM_INFO, bytes([SYSINFO_SERIAL]))
    _check_error(resp, CMD_SYSTEM_INFO)
    data = resp[3 : 3 + resp[2]]
    return data.split(b"\x00", 1)[0].decode("ascii", errors="replace")


def get_hardware_id(hid: KatanaHID) -> str:
    resp = hid.send(CMD_SYSTEM_INFO, bytes([SYSINFO_HW]))
    _check_error(resp, CMD_SYSTEM_INFO)
    data = resp[3 : 3 + resp[2]]
    return data.hex()


def get_system_info(hid: KatanaHID) -> dict[str, str]:
    return {
        "firmware": get_firmware_version(hid),
        "serial": get_serial_number(hid),
        "hardware_id": get_hardware_id(hid),
    }


# ── Input selection ──────────────────────────────────────────────────────────

def get_input(hid: KatanaHID) -> str:
    """Query the currently active input source."""
    resp = hid.send(CMD_INPUT, bytes([INPUT_SUB_QUERY]))
    _check_error(resp, CMD_INPUT)
    data = resp[3 : 3 + resp[2]]
    if len(data) >= 2:
        source_id = data[1]
        return INPUT_NAMES.get(source_id, f"unknown(0x{source_id:02x})")
    raise KatanaError("Unexpected response for input query")


def set_input(hid: KatanaHID, source: str) -> str:
    """Switch the active input source. Returns the new active source name."""
    source_lower = source.lower()
    if source_lower not in INPUT_BY_NAME:
        raise ValueError(
            f"Unknown input '{source}'. "
            f"Choose from: {', '.join(INPUT_BY_NAME)}"
        )
    source_id = INPUT_BY_NAME[source_lower]
    resp = hid.send(CMD_INPUT, bytes([INPUT_SUB_SET, source_id]))
    # The device may return an error followed by an input-status response.
    # Read a second response to get the actual state.
    resp2 = hid.send(CMD_INPUT, bytes([INPUT_SUB_QUERY]))
    _check_error(resp2, CMD_INPUT)
    data = resp2[3 : 3 + resp2[2]]
    if len(data) >= 2:
        return INPUT_NAMES.get(data[1], f"unknown(0x{data[1]:02x})")
    return source_lower


# ── Profile selection ────────────────────────────────────────────────────────

def set_profile(hid: KatanaHID, profile: int | str) -> str:
    """Activate a profile by number (0-5) or name."""
    if isinstance(profile, str):
        profile_lower = profile.lower()
        if profile_lower not in PROFILE_BY_NAME:
            raise ValueError(
                f"Unknown profile '{profile}'. "
                f"Choose from: {', '.join(PROFILE_BY_NAME)}"
            )
        profile_num = PROFILE_BY_NAME[profile_lower]
    else:
        profile_num = int(profile)
        if profile_num not in PROFILE_NAMES:
            raise ValueError(f"Profile number must be 0-5, got {profile_num}")

    resp = hid.send(CMD_PROFILE, bytes([0x02, 0x00, profile_num]))
    _check_error(resp, CMD_PROFILE)
    data = resp[3 : 3 + resp[2]]
    if len(data) >= 2:
        returned = data[1] & 0x7F  # strip possible 0x80 XOR flag
        return PROFILE_NAMES.get(returned, f"profile-{returned}")
    return PROFILE_NAMES.get(profile_num, str(profile_num))


# ── Volume (read-only from HID, set via ALSA) ───────────────────────────────

def get_volume_from_response(resp: bytes) -> int | None:
    """Parse a volume notification (command 0x23).

    This is typically received asynchronously when the volume knob is turned.
    Returns the volume level as displayed on the device (0-50 range typically).
    """
    if len(resp) < 5 or resp[0] != MAGIC or resp[1] != CMD_VOLUME:
        return None
    return resp[4]


# ── EQ registers ─────────────────────────────────────────────────────────────

def get_eq_register(hid: KatanaHID, reg_hi: int, reg_lo: int) -> bytes:
    """Read an EQ register. Returns the raw data payload."""
    resp = hid.send(CMD_EQ_GET, bytes([reg_hi, reg_lo, 0x00]))
    _check_error(resp, CMD_EQ_GET)
    return resp[3 : 3 + resp[2]]


def set_eq_register(
    hid: KatanaHID, reg_hi: int, reg_lo: int, value: bytes
) -> bytes:
    """Write an EQ register. Returns the raw data payload of the response."""
    payload = bytes([reg_hi, reg_lo, 0x00, 0x00]) + value
    resp = hid.send(CMD_EQ_SET, payload[:7])
    _check_error(resp, CMD_EQ_SET)
    return resp[3 : 3 + resp[2]]


def get_all_eq(hid: KatanaHID) -> dict[str, str]:
    """Read all known EQ registers and return hex-encoded raw values.

    Returns 'unsupported' for registers that the firmware does not expose
    (error 0x83 is common on older firmware versions).
    """
    result: dict[str, str] = {}
    for name, (hi, lo) in EQ_REGISTERS.items():
        try:
            data = get_eq_register(hid, hi, lo)
            result[name] = data.hex()
        except (KatanaError, TimeoutError):
            result[name] = "unsupported"
    return result


# ── Lighting ─────────────────────────────────────────────────────────────────

def set_lighting(hid: KatanaHID, enabled: bool) -> bool:
    """Turn lighting on or off for the current profile."""
    value = 0x01 if enabled else 0x00
    resp = hid.send(CMD_LIGHTING, bytes([LIGHT_SUB_ON_OFF, value]))
    # Device may return error 0x02, but the command still works
    return enabled


def get_lighting_name(hid: KatanaHID, profile: int = 0) -> str:
    """Get the lighting pattern name for a profile (0-5).

    Returns 'Lights Off' if lighting is disabled for that profile.
    """
    resp = hid.send(CMD_LIGHTING, bytes([LIGHT_SUB_GET_NAME, profile]))
    _check_error(resp, CMD_LIGHTING)
    data = resp[3 : 3 + resp[2]]
    if len(data) < 6:
        return "unknown"
    # Name starts at offset 5, encoded as UTF-16LE (char + 0x00)
    raw_name = data[5:]
    return raw_name.decode("utf-16-le", errors="replace").rstrip("\x00")
