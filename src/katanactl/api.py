"""FastAPI REST-API for the Sound BlasterX Katana."""

from __future__ import annotations

import subprocess
from contextlib import contextmanager
from typing import Generator

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .commands import (
    KatanaError,
    get_all_eq,
    get_input,
    get_lighting_name,
    get_system_info,
    set_input,
    set_lighting,
    set_profile,
)
from .protocol import (
    EQ_DESCRIPTIONS,
    EQ_REGISTERS,
    INPUT_BY_NAME,
    INPUT_DESCRIPTIONS,
    INPUT_NAMES,
    PROFILE_BY_NAME,
    PROFILE_DESCRIPTIONS,
    PROFILE_NAMES,
)
from .transport import KatanaHID, find_hidraw_device
from .volume import get_volume, set_mute, set_volume

app = FastAPI(
    title="katanactl API",
    description="REST API for controlling the Creative Sound BlasterX Katana",
    version="0.1.0",
)

DEVICE_UNAVAILABLE = (
    "Sound BlasterX Katana is not available. "
    "The device may be powered off or disconnected."
)


@contextmanager
def _hid() -> Generator[KatanaHID, None, None]:
    try:
        with KatanaHID() as hid:
            yield hid
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail=DEVICE_UNAVAILABLE)
    except KatanaError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except (OSError, TimeoutError) as exc:
        raise HTTPException(status_code=503, detail=f"HID I/O error: {exc}")


# ── Models ───────────────────────────────────────────────────────────────────

class InputRequest(BaseModel):
    source: str = Field(
        ...,
        description="Input source name",
        examples=["computer", "bluetooth", "aux", "optical", "usb"],
    )


class ProfileRequest(BaseModel):
    profile: str | int = Field(
        ...,
        description="Profile name or number (0-5)",
        examples=["neutral", 0, "profile-1", 3],
    )


class VolumeRequest(BaseModel):
    percent: int = Field(..., ge=0, le=100, description="Volume 0-100")


class MuteRequest(BaseModel):
    muted: bool


class LightingRequest(BaseModel):
    enabled: bool = Field(..., description="Turn lighting on (true) or off (false)")


# ── Reference endpoints ──────────────────────────────────────────────────────

@app.get("/inputs")
def api_list_inputs() -> list[dict]:
    """List all available input sources with their API names."""
    return [
        {"name": name, "description": INPUT_DESCRIPTIONS[name]}
        for name in INPUT_BY_NAME
    ]


@app.get("/profiles")
def api_list_profiles() -> list[dict]:
    """List all available audio profiles with their API names."""
    return [
        {"id": num, "name": name, "description": PROFILE_DESCRIPTIONS[name]}
        for num, name in PROFILE_NAMES.items()
    ]


@app.get("/eq/registers")
def api_list_eq_registers() -> list[dict]:
    """List all available EQ registers with their API names."""
    return [
        {"name": name, "description": EQ_DESCRIPTIONS[name]}
        for name in EQ_REGISTERS
    ]


# ── Device endpoints ─────────────────────────────────────────────────────────

@app.get("/info")
def api_info() -> dict:
    """Get system info (firmware, serial, hardware ID)."""
    with _hid() as hid:
        return get_system_info(hid)


@app.get("/input")
def api_get_input() -> dict:
    """Get the currently active input source."""
    with _hid() as hid:
        return {"input": get_input(hid)}


@app.post("/input")
def api_set_input(req: InputRequest) -> dict:
    """Switch the active input source."""
    try:
        with _hid() as hid:
            result = set_input(hid, req.source)
        return {"input": result}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.post("/profile")
def api_set_profile(req: ProfileRequest) -> dict:
    """Switch audio profile."""
    try:
        with _hid() as hid:
            result = set_profile(hid, req.profile)
        return {"profile": result}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/volume")
def api_get_volume() -> dict:
    """Get current volume level and mute state via ALSA."""
    try:
        return get_volume()
    except subprocess.CalledProcessError:
        raise HTTPException(status_code=503, detail=DEVICE_UNAVAILABLE)


@app.post("/volume")
def api_set_volume(req: VolumeRequest) -> dict:
    """Set volume level (0-100) via ALSA."""
    try:
        return set_volume(req.percent)
    except subprocess.CalledProcessError:
        raise HTTPException(status_code=503, detail=DEVICE_UNAVAILABLE)


@app.post("/mute")
def api_set_mute(req: MuteRequest) -> dict:
    """Mute or unmute speakers via ALSA."""
    try:
        return set_mute(req.muted)
    except subprocess.CalledProcessError:
        raise HTTPException(status_code=503, detail=DEVICE_UNAVAILABLE)


@app.get("/eq")
def api_get_eq() -> dict:
    """Read all EQ register values (raw hex).

    Note: EQ registers may return 'unsupported' on some firmware versions.
    """
    with _hid() as hid:
        return get_all_eq(hid)


@app.get("/lighting")
def api_get_lighting() -> dict:
    """Get the lighting pattern name for the current profile."""
    with _hid() as hid:
        name = get_lighting_name(hid)
    return {"pattern": name}


@app.post("/lighting")
def api_set_lighting(req: LightingRequest) -> dict:
    """Turn lighting on or off."""
    with _hid() as hid:
        result = set_lighting(hid, req.enabled)
    return {"enabled": result}


@app.get("/health")
def api_health() -> dict:
    """Health check -- reports whether the Katana HID device is reachable."""
    try:
        device = find_hidraw_device()
        return {"status": "ok", "device": device}
    except FileNotFoundError:
        return {"status": "unavailable", "device": None}
