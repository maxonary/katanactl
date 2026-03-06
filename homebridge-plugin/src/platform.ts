import type {
  API,
  DynamicPlatformPlugin,
  Logging,
  PlatformAccessory,
  PlatformConfig,
} from 'homebridge';
import { KatanaAccessory } from './katana-accessory';
import { KatanaApiClient } from './api-client';

const PLUGIN_NAME = 'homebridge-katana';
const PLATFORM_NAME = 'SoundBlasterKatana';

export class KatanaPlatform implements DynamicPlatformPlugin {
  private readonly api: API;
  private readonly log: Logging;
  private readonly config: PlatformConfig;
  private readonly client: KatanaApiClient;
  private readonly accessories: PlatformAccessory[] = [];

  constructor(log: Logging, config: PlatformConfig, api: API) {
    this.log = log;
    this.config = config;
    this.api = api;

    const host = (config.host as string) || 'http://localhost:8099';
    this.client = new KatanaApiClient(host, log);

    this.log.info('Katana platform initializing, API host:', host);

    api.on('didFinishLaunching', () => {
      this.discoverDevice();
    });
  }

  configureAccessory(accessory: PlatformAccessory): void {
    this.log.info('Restoring cached accessory:', accessory.displayName);
    this.accessories.push(accessory);
  }

  private async discoverDevice(): Promise<void> {
    const health = await this.client.getHealth();
    if (!health || health.status !== 'ok') {
      this.log.warn(
        'Katana device not available at startup. ' +
        'The accessory will be registered but may not respond until the device is powered on.',
      );
    }

    const uuid = this.api.hap.uuid.generate('katana-soundbar');
    const name = (this.config.name as string) || 'Katana';

    const existing = this.accessories.find(a => a.UUID === uuid);
    if (existing) {
      this.log.info('Reusing existing accessory:', existing.displayName);
      new KatanaAccessory(this.log, this.api, existing, this.client);
    } else {
      this.log.info('Adding new accessory:', name);
      const accessory = new this.api.platformAccessory(name, uuid, this.api.hap.Categories.TV_SET_TOP_BOX);
      new KatanaAccessory(this.log, this.api, accessory, this.client);
      this.api.publishExternalAccessories(PLUGIN_NAME, [accessory]);
    }
  }
}
