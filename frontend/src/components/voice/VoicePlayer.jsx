import { useEffect, useRef } from 'react';

function VoicePlayer({ src, autoPlay = true, label = '语音回答' }) {
  const audioRef = useRef(null);

  useEffect(() => {
    if (autoPlay && src && audioRef.current) {
      audioRef.current.play().catch(() => {
        /* 浏览器可能拦截自动播放，用户可手动点击播放 */
      });
    }
  }, [src, autoPlay]);

  if (!src) return null;

  return (
    <section className="voice-player">
      <p className="voice-player__label">{label}</p>
      <audio ref={audioRef} controls src={src} className="voice-player__audio" />
    </section>
  );
}

export default VoicePlayer;
