import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import { submitVoiceMeet } from '../services/api';
import { base64ToAudioUrl, revokeAudioUrl } from '../utils';

const AppContext = createContext(null);

const IDLE = 'idle';
const RECORDING = 'recording';
const UPLOADING = 'uploading';
const SUCCESS = 'success';
const ERROR = 'error';

export function AppProvider({ children }) {
  const [status, setStatus] = useState(IDLE);
  const [error, setError] = useState(null);
  const [transcript, setTranscript] = useState('');
  const [slots, setSlots] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [answer, setAnswer] = useState('');
  const [responseAudioUrl, setResponseAudioUrl] = useState(null);

  const clearResponseAudio = useCallback(() => {
    setResponseAudioUrl((prev) => {
      revokeAudioUrl(prev);
      return null;
    });
  }, []);

  const resetSession = useCallback(() => {
    clearResponseAudio();
    setStatus(IDLE);
    setError(null);
    setTranscript('');
    setSlots(null);
    setRecommendations([]);
    setAnswer('');
  }, [clearResponseAudio]);

  const submitAudio = useCallback(
    async (audioBlob) => {
      setStatus(UPLOADING);
      setError(null);
      clearResponseAudio();

      try {
        const data = await submitVoiceMeet(audioBlob);

        setTranscript(data.transcript ?? '');
        setSlots(data.slots ?? null);
        setRecommendations(data.recommendations ?? []);
        setAnswer(data.answer ?? '');

        if (data.audioUrl) {
          setResponseAudioUrl(data.audioUrl);
        } else if (data.audioBase64) {
          setResponseAudioUrl(
            base64ToAudioUrl(data.audioBase64, data.audioContentType ?? 'audio/mpeg'),
          );
        }

        setStatus(SUCCESS);
        return data;
      } catch (err) {
        setError(err.message || '请求失败，请稍后重试');
        setStatus(ERROR);
        throw err;
      }
    },
    [clearResponseAudio],
  );

  const value = useMemo(
    () => ({
      status,
      error,
      transcript,
      slots,
      recommendations,
      answer,
      responseAudioUrl,
      isUploading: status === UPLOADING,
      isSuccess: status === SUCCESS,
      submitAudio,
      resetSession,
    }),
    [
      status,
      error,
      transcript,
      slots,
      recommendations,
      answer,
      responseAudioUrl,
      submitAudio,
      resetSession,
    ],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useAppContext() {
  const ctx = useContext(AppContext);
  if (!ctx) {
    throw new Error('useAppContext 必须在 AppProvider 内使用');
  }
  return ctx;
}
