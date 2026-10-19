import type { API, CharacteristicValue, Logging, PlatformAccessory, Service } from 'homebridge';
import { KatanaApiClient, type KatanaLighting } from './api-client';

/** A separate light accessory keeps LED controls distinct from audio volume. */
export class KatanaLight {
  private readonly service: Service;
  private enabled = false;
  private hue = 0;
  private saturation = 100;
  private brightness = 30;
  private dirtyColor = false;
  private timer?: ReturnType<typeof setTimeout>;
  private pending: Array<{resolve: () => void; reject: (error: Error) => void}> = [];
  private writes: Promise<void> = Promise.resolve();
  private busy = 0;
  private poll?: ReturnType<typeof setInterval>;

  constructor(private log: Logging, private api: API, accessory: PlatformAccessory, private client: KatanaApiClient) {
    const {Service: S, Characteristic: C} = api.hap;
    accessory.getService(S.AccessoryInformation)!
      .setCharacteristic(C.Manufacturer, 'Creative Technology')
      .setCharacteristic(C.Model, 'Sound BlasterX Katana Lighting')
      .setCharacteristic(C.SerialNumber, 'Katana-LED');
    this.service = accessory.getServiceById(S.Lightbulb, 'katana-rgb') ||
      accessory.addService(S.Lightbulb, 'Katana Licht', 'katana-rgb');
    this.service.setCharacteristic(C.Name, 'Katana Licht');
    this.service.getCharacteristic(C.On).onGet(() => this.enabled).onSet(value => {
      this.enabled = value as boolean;
      return this.queueChange(false);
    });
    for (const [characteristic, field] of [[C.Hue,'hue'], [C.Saturation,'saturation'], [C.Brightness,'brightness']] as const) {
      this.service.getCharacteristic(characteristic).onGet(() => this[field]).onSet((value: CharacteristicValue) => {
        this[field] = value as number;
        return this.queueChange(true);
      });
    }
    void this.refresh();
    this.poll = setInterval(() => void this.refresh(), 15_000);
    api.on('shutdown', () => {
      if(this.poll) clearInterval(this.poll);
      if(this.timer) clearTimeout(this.timer);
      for(const p of this.pending) p.reject(new Error('Homebridge is shutting down'));
      this.pending=[];
    });
  }

  private queueChange(colorChanged: boolean): Promise<void> {
    this.dirtyColor ||= colorChanged;
    if(this.timer) clearTimeout(this.timer);
    const promise = new Promise<void>((resolve,reject) => this.pending.push({resolve,reject}));
    this.timer=setTimeout(() => {
      this.timer=undefined;
      const pending=this.pending.splice(0);
      const changeColor=this.dirtyColor;this.dirtyColor=false;
      const color={hue:this.hue,saturation:this.saturation,brightness:this.brightness,enabled:this.enabled};
      this.busy++;
      this.writes=this.writes.then(async () => {
        try {
          let state: KatanaLighting | null;
          if(changeColor) state=await this.client.setLightingColor(color);
          else {await this.client.setLighting(color.enabled);state=await this.client.getLightingState();}
          if(!state) throw new Error('Katana light state unavailable');
          if(!this.pending.length && !this.timer) this.apply(state);
          for(const p of pending) p.resolve();
        } catch(error) {
          for(const p of pending) p.reject(error instanceof Error ? error : new Error(String(error)));
        } finally { this.busy--; }
      });
    },180);
    return promise;
  }

  private apply(state: KatanaLighting): void {
    const C=this.api.hap.Characteristic;
    this.enabled=state.enabled;
    this.service.updateCharacteristic(C.On,this.enabled);
    if(state.hue !== undefined && state.saturation !== undefined && state.brightness !== undefined) {
      this.hue=state.hue;this.saturation=state.saturation;this.brightness=state.brightness;
      this.service.updateCharacteristic(C.Hue,this.hue);
      this.service.updateCharacteristic(C.Saturation,this.saturation);
      this.service.updateCharacteristic(C.Brightness,this.brightness);
    }
  }

  private async refresh(): Promise<void> {
    if(this.busy || this.timer) return;
    try {
      const state=await this.client.getLightingState();
      if(state && !this.busy && !this.timer) this.apply(state);
    } catch(error) { this.log.debug('Katana lighting unavailable:', String(error)); }
  }
}
