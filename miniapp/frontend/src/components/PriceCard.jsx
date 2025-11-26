function PriceCard({ title, source, data, color }) {
  const formatPrice = (price) => {
    if (!price) return 'N/A'
    return parseFloat(price).toFixed(6)
  }

  const formatChange = (change) => {
    if (change === null || change === undefined) return 'N/A'
    return parseFloat(change).toFixed(2)
  }

  const isPositive = data.change_24h > 0
  const changeClass = isPositive ? 'positive' : 'negative'

  return (
    <div className="card">
      <div className="card-title" style={{ color }}>
        {title}
      </div>

      <div className="price-card">
        <div>
          <div className="price-label">{data.pair || 'HOLDER'}</div>
          <div className="price-value">
            ${formatPrice(data.price_usd || data.price)}
          </div>
        </div>

        <div className={`price-change ${changeClass}`}>
          {isPositive ? '↑' : '↓'} {formatChange(data.change_24h)}%
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-item">
          <div className="stat-label">24h High</div>
          <div className="stat-value">${formatPrice(data.high_24h)}</div>
        </div>

        <div className="stat-item">
          <div className="stat-label">24h Low</div>
          <div className="stat-value">${formatPrice(data.low_24h)}</div>
        </div>

        <div className="stat-item">
          <div className="stat-label">24h Volume</div>
          <div className="stat-value">
            ${data.volume_24h ? parseFloat(data.volume_24h).toLocaleString() : 'N/A'}
          </div>
        </div>

        {data.bid && data.ask && (
          <div className="stat-item">
            <div className="stat-label">Spread</div>
            <div className="stat-value">
              {((data.ask - data.bid) / data.bid * 100).toFixed(3)}%
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default PriceCard
