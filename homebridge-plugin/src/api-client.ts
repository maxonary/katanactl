import type { Logger } from 'homebridge';

export interface KatanaInfo {
  firmware: string;
  serial: string;
  hardware_id: string;
}

export interface KatanaVolume {
  percent: number | null;
  muted: boolean | null;
}

export interface KatanaInput {
  input: string;
}

export interface KatanaLighting {
  pattern: string;
}

export interface KatanaHealth {
  status: string;
  device: string | null;
}

const INPUT_NAMES = ['bluetooth', 'aux', 'optical', 'usb', 'computer'] as const;
export type InputName = typeof INPUT_NAMES[number];

export const INPUT_ID_MAP: Record<number, InputName> = {
  1: 'bluetooth',
  2: 'aux',
  3: 'optical',
  4: 'usb',
  5: 'computer',
};

export const INPUT_NAME_TO_ID: Record<InputName, number> = {
  bluetooth: 1,
  aux: 2,
  optical: 3,
  usb: 4,
  computer: 5,
};

export const INPUT_LABELS: Record<InputName, string> = {
  bluetooth: 'Bluetooth',
  aux: 'AUX',
  optical: 'Optical',
  usb: 'USB',
  computer: 'Computer',
};

export class KatanaApiClient {
  private readonly baseUrl: string;
  private readonly log: Logger;

  constructor(host: string, log: Logger) {
    this.baseUrl = host.replace(/\/+$/, '');
    this.log = log;
  }

  private async request<T>(path: string, init?: RequestInit): Promise<T | null> {
    const url = `${this.baseUrl}${path}`;
    try {
      const resp = await fetch(url, {
        ...init,
        headers: { 'Content-Type': 'application/json', ...init?.headers },
        signal: AbortSignal.timeout(5000),
      });
      if (!resp.ok) {
        this.log.warn(`API ${init?.method ?? 'GET'} ${path} returned ${resp.status}`);
        return null;
      }
      return await resp.json() as T;
    } catch (err) {
      this.log.debug(`API ${path} error: ${err}`);
      return null;
    }
  }

  async getHealth(): Promise<KatanaHealth | null> {
    return this.request<KatanaHealth>('/health');
  }

  async getInfo(): Promise<KatanaInfo | null> {
    return this.request<KatanaInfo>('/info');
  }

  async getInput(): Promise<InputName | null> {
    const data = await this.request<KatanaInput>('/input');
    return (data?.input as InputName) ?? null;
  }

  async setInput(source: InputName): Promise<void> {
    await this.request('/input', {
      method: 'POST',
      body: JSON.stringify({ source }),
    });
  }

  async getVolume(): Promise<KatanaVolume | null> {
    return this.request<KatanaVolume>('/volume');
  }

  async setVolume(percent: number): Promise<void> {
    await this.request('/volume', {
      method: 'POST',
      body: JSON.stringify({ percent: Math.max(0, Math.min(100, percent)) }),
    });
  }

  async setMute(muted: boolean): Promise<void> {
    await this.request('/mute', {
      method: 'POST',
      body: JSON.stringify({ muted }),
    });
  }

  async getLighting(): Promise<boolean | null> {
    const data = await this.request<KatanaLighting>('/lighting');
    if (!data) {
      return null;
    }
    return data.pattern !== 'Lights Off';
  }

  async setLighting(enabled: boolean): Promise<void> {
    await this.request('/lighting', {
      method: 'POST',
      body: JSON.stringify({ enabled }),
    });
  }
}
