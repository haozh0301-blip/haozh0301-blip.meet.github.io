import { API_BASE, API_PATHS } from '../config';

async function parseErrorResponse(response) {
  try {
    const data = await response.json();
    return data.message || data.detail || `请求失败 (${response.status})`;
  } catch {
    return `请求失败 (${response.status})`;
  }
}

/**
 * 上传录音，触发完整后端链路（ASR → 槽位 → 高德 → 回答 → TTS）
 * @param {Blob} audioBlob
 * @param {string} [filename='recording.webm']
 * @returns {Promise<MeetVoiceResponse>}
 */
export async function submitVoiceMeet(audioBlob, filename = 'recording.webm') {
  if (import.meta.env.PROD && !API_BASE) {
    throw new Error(
      '在线 Demo 尚未配置后端地址。请在 GitHub 仓库 Variables 中设置 VITE_API_BASE_URL（Render 后端 URL）。'
    );
  }

  const formData = new FormData();
  formData.append('audio', audioBlob, filename);

  const response = await fetch(`${API_BASE}${API_PATHS.voiceMeet}`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await parseErrorResponse(response));
  }

  return response.json();
}

/** @typedef {{ city: string, address: string }} LocationSlot */
/** @typedef {{ user: LocationSlot, friend: LocationSlot }} MeetSlots */
/** @typedef {{
 *   id?: string,
 *   name: string,
 *   address: string,
 *   distance?: { user?: string, friend?: string },
 *   duration?: { user?: string, friend?: string },
 *   route?: string,
 * }} MeetRecommendation */
/** @typedef {{
 *   transcript: string,
 *   slots: MeetSlots,
 *   recommendations: MeetRecommendation[],
 *   answer: string,
 *   audioBase64?: string,
 *   audioUrl?: string,
 *   audioContentType?: string,
 * }} MeetVoiceResponse */

export const voiceService = { submitVoiceMeet };
export const recommendationService = {};
