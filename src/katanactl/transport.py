"""Low-level HID transport for the Sound BlasterX Katana.

Opens /dev/hidraw* and provides send/receive of 64-byte HID reports
using the Katana's command framing (magic byte 0x5A).

The device may send unsolicited status messages (e.g. input-status 0x9C/0x06)
at any time, so the transport drains stale data before sending a command and
retries reads until it finds the expected response command byte.
"""

from __future__ import annotations

import fcntl
import glob
import os
import select
import time
from pathlib import Path

MAGIC = 0x5A
HID_REPORT_SIZE = 64
CMD_ERROR = 0x02

VENDOR_ID = "041e"
PRODUCT_ID = "3247"

MAX_READ_ATTEMPTS = 10
READ_TIMEOUT_S = 0.5


def find_hidraw_device() -> str:
    """Auto-detect the Katana's 64-byte control hidraw device (interface 4)."""
    for path in sorted(glob.glob("/sys/class/hidraw/hidraw*/device/uevent")):
        try:
            text = Path(path).read_text()
        except OSError:
            continue
        if VENDOR_ID.upper() not in text or PRODUCT_ID.upper() not in text:
            continue
        if "input4" in text:
            hidraw_name = path.split("/")[4]
            return f"/dev/{hidraw_name}"
    raise FileNotFoundError(
        "No Sound BlasterX Katana control interface found. "
        "Is the device connected via USB?"
    )


class KatanaHID:
    """Manage a raw HID connection to the Katana."""

    def __init__(self, device_path: str | None = None):
        self._path = device_path or find_hidraw_device()
        self._fd: int | None = None

    def open(self) -> None:
        self._fd = os.open(self._path, os.O_RDWR | os.O_NONBLOCK)
        # Serialize API/CLI clients across processes, including read-modify-write.
        fcntl.flock(self._fd, fcntl.LOCK_EX)

    def close(self) -> None:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None

    def __enter__(self) -> KatanaHID:
        self.open()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def _drain(self) -> None:
        """Discard any buffered unsolicited messages."""
        if self._fd is None:
            return
        while True:
            r, _, _ = select.select([self._fd], [], [], 0)
            if not r:
                break
            try:
                os.read(self._fd, HID_REPORT_SIZE)
            except BlockingIOError:
                break

    def _read_with_timeout(self, timeout: float = READ_TIMEOUT_S) -> bytes | None:
        """Read one 64-byte report, returning None on timeout."""
        if self._fd is None:
            raise RuntimeError("HID device not open")
        r, _, _ = select.select([self._fd], [], [], timeout)
        if not r:
            return None
        try:
            return bytes(os.read(self._fd, HID_REPORT_SIZE))
        except BlockingIOError:
            return None

    def send(self, command: int, payload: bytes = b"") -> bytes:
        """Send a command and return the matching 64-byte response.

        Frame format: [0x5A] [cmd] [len] [payload...]  (padded to 64 bytes)

        Drains stale data first, then retries reads up to MAX_READ_ATTEMPTS
        to skip unsolicited messages and find the expected response.
        """
        if self._fd is None:
            raise RuntimeError("HID device not open")

        self._drain()

        frame = bytearray(HID_REPORT_SIZE)
        frame[0] = MAGIC
        frame[1] = command
        frame[2] = len(payload)
        frame[3 : 3 + len(payload)] = payload

        os.write(self._fd, bytes(frame))

        for _ in range(MAX_READ_ATTEMPTS):
            resp = self._read_with_timeout()
            if resp is None:
                raise TimeoutError(
                    f"No response for command 0x{command:02x} "
                    f"after {READ_TIMEOUT_S}s"
                )
            if len(resp) >= 2 and resp[0] == MAGIC:
                if command == 0x3A and payload:
                    # Lighting writes also emit name/status notifications. Match
                    # the subcommand, including Creative's 0x02 success ACK.
                    if resp[1] == command and len(resp) > 3 and resp[3] == payload[0]:
                        return resp
                    if resp[1] == CMD_ERROR and len(resp) > 5 and resp[3] == command and resp[5] == payload[0]:
                        return resp
                elif resp[1] == command or resp[1] == CMD_ERROR:
                    return resp

        raise TimeoutError(
            f"Did not receive matching response for command 0x{command:02x} "
            f"after {MAX_READ_ATTEMPTS} reads"
        )

    def read_unsolicited(self, timeout: float = 0.1) -> bytes | None:
        """Read one unsolicited message (e.g. volume change), or None."""
        return self._read_with_timeout(timeout)
