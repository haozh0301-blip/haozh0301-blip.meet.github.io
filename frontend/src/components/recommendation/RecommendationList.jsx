import RecommendationCard from './RecommendationCard';

function RecommendationList({ items = [], emptyText = '暂无推荐结果' }) {
  if (!items.length) {
    return <p className="recommendation-list__empty">{emptyText}</p>;
  }

  return (
    <section className="recommendation-list">
      <h2 className="recommendation-list__title">推荐碰面地点</h2>
      <div className="recommendation-list__grid">
        {items.map((item, index) => (
          <RecommendationCard
            key={item.id ?? `${item.name}-${index}`}
            item={item}
            index={index}
          />
        ))}
      </div>
    </section>
  );
}

export default RecommendationList;
