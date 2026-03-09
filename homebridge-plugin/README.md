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
- **Switch** — toggle the Katana LED lighting strip on/off

## More Information

See the [katanactl repository](https://github.com/maxonary/katanactl) for REST API setup and full documentation.
