/** 开发环境走 Vite 代理；生产/Demo 通过 VITE_API_BASE_URL 指定后端地址 */
export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '';

export const API_PATHS = {
  voiceMeet: '/api/meet/voice',
};

export const IS_DEMO = import.meta.env.PROD && Boolean(import.meta.env.VITE_BASE_PATH);
