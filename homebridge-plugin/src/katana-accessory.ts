import type {
  API,
  CharacteristicGetCallback,
  CharacteristicSetCallback,
  CharacteristicValue,
  Logging,
  PlatformAccessory,
  Service,
} from 'homebridge';
import {
  INPUT_ID_MAP,
  INPUT_LABELS,
  INPUT_NAME_TO_ID,
  KatanaApiClient,
  type InputName,
} from './api-client';

const VOLUME_STEP = 5;
const POLL_INTERVAL_MS = 15_000;

export class KatanaAccessory {
  private readonly log: Logging;
  private readonly api: API;
  private readonly accessory: PlatformAccessory;
  private readonly client: KatanaApiClient;

  private readonly tvService: Service;
  private readonly speakerService: Service;
  private readonly lightService: Service;

  private currentInput: InputName = 'computer';
  private currentVolume = 50;
  private currentMuted = false;
  private lightOn = false;
  private deviceActive = true;

  constructor(log: Logging, api: API, accessory: PlatformAccessory, client: KatanaApiClient) {
    this.log = log;
    this.api = api;
    this.accessory = accessory;
    this.client = client;

    const { Service: Svc, Characteristic: C } = api.hap;

    // -- Accessory Information --
    const infoService = accessory.getService(Svc.AccessoryInformation) ||
      accessory.addService(Svc.AccessoryInformation);
    infoService
      .setCharacteristic(C.Manufacturer, 'Creative Technology')
      .setCharacteristic(C.Model, 'Sound BlasterX Katana')
      .setCharacteristic(C.SerialNumber, 'Unknown');

    // -- Television Service --
    this.tvService = accessory.getService(Svc.Television) ||
      accessory.addService(Svc.Television, 'Katana', 'katana-tv');

    this.tvService
      .setCharacteristic(C.ConfiguredName, accessory.displayName)
      .setCharacteristic(C.SleepDiscoveryMode, C.SleepDiscoveryMode.ALWAYS_DISCOVERABLE)
      .setCharacteristic(C.ActiveIdentifier, 5);

    this.tvService.getCharacteristic(C.Active)
      .onGet(() => this.deviceActive ? C.Active.ACTIVE : C.Active.INACTIVE)
      .onSet((value: CharacteristicValue) => {
        this.deviceActive = value === C.Active.ACTIVE;
        this.log.info('Power:', this.deviceActive ? 'ON' : 'OFF');
      });

    this.tvService.getCharacteristic(C.ActiveIdentifier)
      .onGet(() => INPUT_NAME_TO_ID[this.currentInput] ?? 5)
      .onSet(async (value: CharacteristicValue) => {
        const id = value as number;
        const name = INPUT_ID_MAP[id];
        if (name) {
          this.log.info('Switching input to:', name);
          await this.client.setInput(name);
          this.currentInput = name;
        }
      });

    this.tvService.getCharacteristic(C.RemoteKey)
      .onSet(async (value: CharacteristicValue) => {
        const key = value as number;
        if (key === C.RemoteKey.ARROW_UP) {
          await this.adjustVolume(VOLUME_STEP);
        } else if (key === C.RemoteKey.ARROW_DOWN) {
          await this.adjustVolume(-VOLUME_STEP);
        }
      });

    // -- Television Speaker --
    this.speakerService = accessory.getService(Svc.TelevisionSpeaker) ||
      accessory.addService(Svc.TelevisionSpeaker, 'Katana Speaker', 'katana-speaker');

    this.speakerService
      .setCharacteristic(C.Active, C.Active.ACTIVE)
      .setCharacteristic(C.VolumeControlType, C.VolumeControlType.ABSOLUTE);

    this.speakerService.getCharacteristic(C.Mute)
      .onGet(() => this.currentMuted)
      .onSet(async (value: CharacteristicValue) => {
        this.currentMuted = value as boolean;
        this.log.info('Mute:', this.currentMuted);
        await this.client.setMute(this.currentMuted);
      });

    this.speakerService.getCharacteristic(C.Volume)
      .onGet(() => this.currentVolume)
      .onSet(async (value: CharacteristicValue) => {
        this.currentVolume = value as number;
        this.log.info('Volume:', this.currentVolume);
        await this.client.setVolume(this.currentVolume);
      });

    this.speakerService.getCharacteristic(C.VolumeSelector)
      .onSet(async (value: CharacteristicValue) => {
        const increment = value === C.VolumeSelector.INCREMENT ? VOLUME_STEP : -VOLUME_STEP;
        await this.adjustVolume(increment);
      });

    this.tvService.addLinkedService(this.speakerService);

    // -- Input Sources --
    for (const [idStr, name] of Object.entries(INPUT_ID_MAP)) {
      const id = Number(idStr);
      const label = INPUT_LABELS[name];
      const subtype = `katana-input-${name}`;

      let inputService = accessory.getServiceById(Svc.InputSource, subtype);
      if (!inputService) {
        inputService = accessory.addService(Svc.InputSource, name, subtype);
      }

      inputService
        .setCharacteristic(C.Identifier, id)
        .setCharacteristic(C.ConfiguredName, label)
        .setCharacteristic(C.IsConfigured, C.IsConfigured.CONFIGURED)
        .setCharacteristic(C.InputSourceType, C.InputSourceType.OTHER)
        .setCharacteristic(C.CurrentVisibilityState, C.CurrentVisibilityState.SHOWN);

      this.tvService.addLinkedService(inputService);
    }

    // -- Lightbulb Service --
    this.lightService = accessory.getService(Svc.Lightbulb) ||
      accessory.addService(Svc.Lightbulb, 'Katana LED', 'katana-light');

    this.lightService.getCharacteristic(C.On)
      .onGet(() => this.lightOn)
      .onSet(async (value: CharacteristicValue) => {
        this.lightOn = value as boolean;
        this.log.info('Lighting:', this.lightOn ? 'ON' : 'OFF');
        await this.client.setLighting(this.lightOn);
      });

    // -- Initial state & polling --
    this.refreshState();
    setInterval(() => this.refreshState(), POLL_INTERVAL_MS);
  }

  private async adjustVolume(step: number): Promise<void> {
    this.currentVolume = Math.max(0, Math.min(100, this.currentVolume + step));
    this.log.info('Volume:', this.currentVolume);
    await this.client.setVolume(this.currentVolume);
    this.speakerService.updateCharacteristic(this.api.hap.Characteristic.Volume, this.currentVolume);
  }

  private async refreshState(): Promise<void> {
    try {
      const [volume, input, lighting, info] = await Promise.all([
        this.client.getVolume(),
        this.client.getInput(),
        this.client.getLighting(),
        this.client.getInfo(),
      ]);

      const C = this.api.hap.Characteristic;

      if (volume) {
        if (volume.percent !== null) {
          this.currentVolume = volume.percent;
          this.speakerService.updateCharacteristic(C.Volume, this.currentVolume);
        }
        if (volume.muted !== null) {
          this.currentMuted = volume.muted;
          this.speakerService.updateCharacteristic(C.Mute, this.currentMuted);
        }
      }

      if (input) {
        this.currentInput = input;
        const id = INPUT_NAME_TO_ID[input];
        if (id) {
          this.tvService.updateCharacteristic(C.ActiveIdentifier, id);
        }
      }

      if (lighting !== null) {
        this.lightOn = lighting;
        this.lightService.updateCharacteristic(C.On, this.lightOn);
      }

      if (info) {
        const infoSvc = this.accessory.getService(this.api.hap.Service.AccessoryInformation);
        if (infoSvc) {
          infoSvc.updateCharacteristic(C.SerialNumber, info.serial || 'Unknown');
          infoSvc.updateCharacteristic(C.FirmwareRevision, info.firmware || '0.0.0');
        }
      }
    } catch (err) {
      this.log.debug('State refresh failed:', String(err));
    }
  }
}
