/** 开发环境走 Vite 代理；生产环境可通过 VITE_API_BASE_URL 指定后端地址 */
export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '';

export const API_PATHS = {
  voiceMeet: '/api/meet/voice',
};
