import { Link } from 'react-router-dom';
import RecommendationList from '../components/recommendation/RecommendationList';
import { useRecommendation } from '../hooks/useRecommendation';

function RecommendPage() {
  const { recommendations, slots, answer } = useRecommendation();

  if (!recommendations.length) {
    return (
      <div className="page recommend-page">
        <h1>推荐详情</h1>
        <p className="recommend-page__empty">还没有推荐结果，请先在首页录音并提交分析。</p>
        <Link to="/" className="btn btn--primary">
          返回首页
        </Link>
      </div>
    );
  }

  return (
    <div className="page recommend-page">
      <header className="recommend-page__header">
        <h1>推荐详情</h1>
        <Link to="/" className="link-back">← 返回首页</Link>
      </header>

      {slots && (
        <section className="result-panel__section">
          <h2>位置信息</h2>
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

      <RecommendationList items={recommendations} />
    </div>
  );
}

export default RecommendPage;
