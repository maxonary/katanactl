# soundblaster-katana-ctl and homebridge-katana

Control the **Creative Sound BlasterX Katana** soundbar from Linux via USB HID.

Provides a **CLI tool**, a **REST API** with Swagger docs, and a **Homebridge** configuration for Apple HomeKit integration.

## Features

- **System info** -- query firmware version, serial number, hardware ID
- **Input switching** -- Bluetooth, AUX, Optical, USB, Computer
- **Audio profiles** -- Neutral, Profile 1-4, Personal
- **Volume & mute** -- via ALSA mixer
- **Lighting** -- on/off control, pattern name query
- **EQ registers** -- read Crystalizer, Surround, Dialog+, Dolby, etc. (firmware-dependent)

## Requirements

- Linux (tested on Raspberry Pi OS)
- Python 3.10+
- Creative Sound BlasterX Katana connected via USB
- The Katana exposes two HID interfaces; this tool uses the 64-byte control interface (`/dev/hidrawN`, USB interface 4)

## Installation

```bash
git clone https://github.com/maxonary/soundblaster-katana-ctl.git
cd soundblaster-katana-ctl
python3 -m venv .venv
.venv/bin/pip install -e .
```

### udev rule (non-root access)

```bash
sudo cp udev/99-katana.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```

## CLI

```bash
# System info
katanactl info

# List available inputs and profiles
katanactl inputs
katanactl profiles

# Query / switch input
katanactl input
katanactl input computer
katanactl input bluetooth

# Switch profile (by number or name)
katanactl profile neutral
katanactl profile 2

# Volume (via ALSA)
katanactl volume
katanactl volume 75
katanactl volume --mute
katanactl volume --unmute

# Lighting
katanactl lighting
katanactl lighting on
katanactl lighting off

# EQ registers (firmware-dependent)
katanactl eq
```

## REST API

Start manually:

```bash
.venv/bin/uvicorn katanactl.api:app --host 0.0.0.0 --port 8099
```

Or as a systemd service:

```bash
sudo cp systemd/katanactl-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now katanactl-api
```

Interactive docs at `http://<host>:8099/docs`.

### Endpoints

| Method | Path            | Description                              |
|--------|-----------------|------------------------------------------|
| GET    | `/inputs`       | List available input sources             |
| GET    | `/profiles`     | List available audio profiles            |
| GET    | `/eq/registers` | List available EQ register names         |
| GET    | `/info`         | Device firmware, serial, hardware ID     |
| GET    | `/input`        | Current input source                     |
| POST   | `/input`        | Switch input `{"source": "bluetooth"}`   |
| POST   | `/profile`      | Switch profile `{"profile": "neutral"}`  |
| GET    | `/volume`       | Current volume & mute state              |
| POST   | `/volume`       | Set volume `{"percent": 75}`             |
| POST   | `/mute`         | Mute/unmute `{"muted": true}`            |
| GET    | `/eq`           | Read all EQ registers                    |
| GET    | `/lighting`     | Current lighting pattern name            |
| POST   | `/lighting`     | Lighting on/off `{"enabled": true}`      |
| GET    | `/health`       | Device availability check                |

## Homebridge (Apple HomeKit)

Install the [homebridge-http-advanced-accessory](https://www.npmjs.com/package/homebridge-http-advanced-accessory) plugin:

```bash
npm install -g homebridge-http-advanced-accessory
```

Then add the accessories from `homebridge/config-snippet.json` to your Homebridge `config.json`. Replace `KATANA_HOST` with the IP of the machine running the API. This gives you:

- **Volume slider** with mute
- **Input switches** (Bluetooth, AUX, Optical, USB)
- **Lighting switch**

All controllable via Siri, the Home app, and automations.

## USB HID Protocol

Based on the reverse-engineered protocol documented at [therion23/KatanaHacking](https://github.com/therion23/KatanaHacking).

Command frame: `[0x5A] [cmd] [len] [payload...]` -- responses are 64 bytes, zero-padded, same structure.

The device sends unsolicited status messages (e.g. input-status changes) at any time. The transport layer drains stale data and retries reads to find the expected response.

## License

MIT


### RGB lighting (Katana firmware 2.0.171220.130)

`GET /lighting` reports the actual LED enabled state, lighting profile/effect,
HSV brightness and RGB when the selected effect has a readable palette.
`POST /lighting` with `{"enabled": true}` controls on/off without changing effects.
`POST /lighting/color` accepts `hue` (0–360), `saturation` (0–100), `brightness`
(0–100), and optional `enabled`. It selects the static Solo effect and verifies
its palette by reading it back. No audio profile, volume or EQ commands are used.

Example:

```sh
curl -H 'Content-Type: application/json' \
  -d '{"hue":30,"saturation":85,"brightness":30,"enabled":true}' \
  http://localhost:8099/lighting/color
```

The wire format was checked against the original application's USB capture
linked from [OpenRGB issue 1065](https://gitlab.com/CalcProgrammer1/OpenRGB/-/issues/1065)
and verified on the connected Katana: palette bytes are brightness, blue, green,
red; the Solo color applies to the whole LED strip. Lighting 0x08 selects an LED
effect, independently of audio profile command 0x1A. Creative's command 0x02 with
status 0x00 is a successful write acknowledgement; lighting responses must also
match the requested subcommand to ignore asynchronous notifications.

Validation: `PYTHONPATH=src python3 -m unittest discover -s tests`. Live red/blue
writes and readback passed; the user visually confirmed the colors. Lighting
settings before deployment are saved on Bedroom in
`/var/backups/katana-lighting-before-colors.json`; original source and plugin
build are in `/var/backups/katana-led-20261019`.
