# homebridge-katana

Homebridge plugin for the **Creative Sound BlasterX Katana** soundbar. Control your Katana through Apple HomeKit and Siri.

## Prerequisites

The [katanactl](https://github.com/maxonary/katanactl) REST API must be running and reachable on your network. By default the plugin connects to `http://localhost:8099`.

## Installation

### Homebridge UI

Search for `homebridge-katana` in the Homebridge UI plugin tab.

### npm

```sh
npm install -g homebridge-katana
```

## Configuration

Add the `SoundBlasterKatana` platform to your Homebridge `config.json`:

```json
{
  "platforms": [
    {
      "platform": "SoundBlasterKatana",
      "name": "Katana",
      "host": "http://localhost:8099"
    }
  ]
}
```

| Field      | Required | Default                  | Description                    |
|------------|----------|--------------------------|--------------------------------|
| `platform` | Yes      | —                        | Must be `SoundBlasterKatana`   |
| `name`     | No       | `Katana`                 | Display name in HomeKit        |
| `host`     | No       | `http://localhost:8099`  | URL of the katanactl REST API  |

## Exposed HomeKit Services

- **Television** — input selector (USB, Bluetooth, Aux, Optical, TOSLINK) with remote-key volume control
- **Dimmable Lightbulb** — brightness slider mapped to volume (0–100%), on/off mapped to mute. Works with Siri: "Set Katana Volume to 40%"
- **Katana Licht** — a separate RGB light with a color wheel, brightness and on/off.
  Color/brightness changes select the static Solo effect. On/off alone preserves
  the selected effect. Audio volume and EQ are independent.

If using a child bridge, pair **Bedroom Katana** (or your configured child bridge)
for the light accessory. The existing external Katana TV keeps its own pairing.
The former LED switch on the TV is replaced by this light.

The API reads the real LED enable flag and verifies color writes through USB.
Rapid HomeKit hue/saturation updates are batched into one write; API/CLI HID
transactions are serialized across processes. Tested on firmware 2.0.171220.130.
Run `npm test` for HomeKit light batching and on/off checks.

## More Information

See the [katanactl repository](https://github.com/maxonary/katanactl) for REST API setup and full documentation.
