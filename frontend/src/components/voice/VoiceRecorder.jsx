import { useEffect, useRef } from 'react';
import { useVoice } from '../../hooks/useVoice';
import { formatDuration } from '../../utils';

function VoiceRecorder({ onSubmit, isUploading, disabled }) {
  const {
    isRecording,
    audioBlob,
    localPreviewUrl,
    error,
    duration,
    startRecording,
    stopRecording,
    reset,
  } = useVoice();

  const handleToggle = () => {
    if (isRecording) {
      stopRecording();
    } else {
      reset();
      startRecording();
    }
  };

  const handleSubmit = () => {
    if (audioBlob && onSubmit) {
      onSubmit(audioBlob);
    }
  };

  return (
    <section className="voice-recorder">
      <div className="voice-recorder__hero">
        <p className="voice-recorder__hint">
          按住下方按钮开始录音，描述你和朋友所在的城市与具体位置
        </p>
        <p className="voice-recorder__example">
          例如：「我在北京中关村，朋友在北京望京 SOHO」
        </p>
      </div>

      <div className="voice-recorder__controls">
        <button
          type="button"
          className={`voice-recorder__btn ${isRecording ? 'voice-recorder__btn--recording' : ''}`}
          onClick={handleToggle}
          disabled={disabled || isUploading}
          aria-pressed={isRecording}
        >
          <span className="voice-recorder__btn-icon" aria-hidden="true">
            {isRecording ? '■' : '🎙'}
          </span>
          <span>{isRecording ? '停止录音' : '开始录音'}</span>
        </button>

        {isRecording && (
          <span className="voice-recorder__timer">{formatDuration(duration)}</span>
        )}
      </div>

      {localPreviewUrl && !isRecording && (
        <div className="voice-recorder__preview">
          <p className="voice-recorder__preview-label">录音预览</p>
          <audio controls src={localPreviewUrl} className="voice-recorder__audio" />
          <div className="voice-recorder__actions">
            <button
              type="button"
              className="btn btn--secondary"
              onClick={reset}
              disabled={isUploading}
            >
              重新录制
            </button>
            <button
              type="button"
              className="btn btn--primary"
              onClick={handleSubmit}
              disabled={!audioBlob || isUploading}
            >
              {isUploading ? '分析中…' : '提交分析'}
            </button>
          </div>
        </div>
      )}

      {error && <p className="voice-recorder__error">{error}</p>}
    </section>
  );
}

export default VoiceRecorder;
