import { Link } from 'react-router-dom';
import VoiceRecorder from '../components/voice/VoiceRecorder';
import VoicePlayer from '../components/voice/VoicePlayer';
import RecommendationList from '../components/recommendation/RecommendationList';
import { useAppContext } from '../context/AppContext';
import { API_BASE, IS_DEMO } from '../config';

function HomePage() {
  const {
    submitAudio,
    isUploading,
    isSuccess,
    error,
    transcript,
    slots,
    recommendations,
    answer,
    responseAudioUrl,
    resetSession,
  } = useAppContext();

  return (
    <div className="page home-page">
      <section className="home-page__intro">
        <h1>Meet · 语音推荐碰面地点</h1>
        <p>说出你和朋友的位置，系统会推荐多个合适的碰面地点，并语音播报结果。</p>
        {IS_DEMO && (
          <p className="home-page__demo-hint">
            在线 Demo
            {API_BASE ? (
              <> · 后端已连接</>
            ) : (
              <> · 等待配置后端地址（<code>VITE_API_BASE_URL</code>）</>
            )}
          </p>
        )}
      </section>

      <VoiceRecorder onSubmit={submitAudio} isUploading={isUploading} />

      {isUploading && (
        <div className="status-panel status-panel--loading">
          <p>正在处理，请稍候…</p>
          <ul className="status-panel__steps">
            <li>语音识别（ASR）</li>
            <li>位置信息提取</li>
            <li>高德地图计算推荐</li>
            <li>DeepSeek 生成回答</li>
            <li>百炼 TTS 合成语音</li>
          </ul>
        </div>
      )}

      {error && (
        <div className="status-panel status-panel--error" role="alert">
          <p>{error}</p>
        </div>
      )}

      {isSuccess && (
        <div className="result-panel">
          {transcript && (
            <section className="result-panel__section">
              <h2>识别文本</h2>
              <p className="result-panel__text">{transcript}</p>
            </section>
          )}

          {slots && (
            <section className="result-panel__section">
              <h2>提取位置</h2>
              <div className="slots-grid">
                <div className="slot-card">
                  <h3>你</h3>
                  <p>{slots.user?.city} · {slots.user?.address}</p>
                </div>
                <div className="slot-card">
                  <h3>朋友</h3>
                  <p>{slots.friend?.city} · {slots.friend?.address}</p>
                </div>
              </div>
            </section>
          )}

          {answer && (
            <section className="result-panel__section">
              <h2>推荐说明</h2>
              <p className="result-panel__text">{answer}</p>
            </section>
          )}

          <VoicePlayer src={responseAudioUrl} />

          {recommendations.length > 0 && (
            <>
              <RecommendationList items={recommendations.slice(0, 2)} />
              {recommendations.length > 2 && (
                <Link to="/recommend" className="link-more">
                  查看全部 {recommendations.length} 个推荐 →
                </Link>
              )}
            </>
          )}

          <button type="button" className="btn btn--secondary" onClick={resetSession}>
            重新开始
          </button>
        </div>
      )}
    </div>
  );
}

export default HomePage;
