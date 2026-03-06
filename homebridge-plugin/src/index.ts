import type { API } from 'homebridge';
import { KatanaPlatform } from './platform';

export default (api: API) => {
  api.registerPlatform('homebridge-katana', 'SoundBlasterKatana', KatanaPlatform);
};
