function RecommendationCard({ item, index }) {
  const userDistance = item.distance?.user;
  const friendDistance = item.distance?.friend;
  const userDuration = item.duration?.user;
  const friendDuration = item.duration?.friend;

  return (
    <article className="recommendation-card">
      <header className="recommendation-card__header">
        <span className="recommendation-card__rank">#{index + 1}</span>
        <h3 className="recommendation-card__title">{item.name}</h3>
      </header>

      <p className="recommendation-card__address">{item.address}</p>

      <dl className="recommendation-card__metrics">
        {(userDistance || userDuration) && (
          <div className="recommendation-card__metric">
            <dt>你的路程</dt>
            <dd>
              {[userDistance, userDuration].filter(Boolean).join(' · ')}
            </dd>
          </div>
        )}
        {(friendDistance || friendDuration) && (
          <div className="recommendation-card__metric">
            <dt>朋友的路程</dt>
            <dd>
              {[friendDistance, friendDuration].filter(Boolean).join(' · ')}
            </dd>
          </div>
        )}
      </dl>

      {item.route && (
        <p className="recommendation-card__route">{item.route}</p>
      )}
    </article>
  );
}

export default RecommendationCard;
