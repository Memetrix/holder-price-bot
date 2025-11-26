function PriceCard({ title, source, data, color }) {
  const formatPrice = (price) => {
    if (!price) return 'N/A'
    return parseFloat(price).toFixed(6)
  }

  const formatChange = (change) => {
    if (change === null || change === undefined) return 'N/A'
    return parseFloat(change).toFixed(2)
  }

  const getChangeClass = (change) => {
    if (change > 0) return 'positive'
    if (change < 0) return 'negative'
    return ''
  }

  const getChangeArrow = (change) => {
    if (change > 0) return '↑'
    if (change < 0) return '↓'
    return '→'
  }

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

        <div className={`price-change ${getChangeClass(data.change_24h)}`}>
          {getChangeArrow(data.change_24h)} {formatChange(data.change_24h)}%
        </div>
      </div>

      {/* Price changes for different periods */}
      {(data.change_1h !== undefined || data.change_6h !== undefined) && (
        <div className="stats-grid" style={{ marginBottom: '8px' }}>
          {data.change_1h !== undefined && (
            <div className="stat-item">
              <div className="stat-label">1h Change</div>
              <div className={`stat-value ${getChangeClass(data.change_1h)}`}>
                {getChangeArrow(data.change_1h)} {formatChange(data.change_1h)}%
              </div>
            </div>
          )}
          {data.change_6h !== undefined && (
            <div className="stat-item">
              <div className="stat-label">6h Change</div>
              <div className={`stat-value ${getChangeClass(data.change_6h)}`}>
                {getChangeArrow(data.change_6h)} {formatChange(data.change_6h)}%
              </div>
            </div>
          )}
        </div>
      )}

      <div className="stats-grid">
        <div className="stat-item">
          <div className="stat-label">24h Volume</div>
          <div className="stat-value">
            ${data.volume_24h ? parseFloat(data.volume_24h).toLocaleString() : 'N/A'}
          </div>
        </div>

        {data.liquidity_usd && (
          <div className="stat-item">
            <div className="stat-label">Liquidity</div>
            <div className="stat-value">
              ${parseFloat(data.liquidity_usd).toLocaleString()}
            </div>
          </div>
        )}

        {(data.buys_24h !== undefined || data.sells_24h !== undefined) && (
          <div className="stat-item">
            <div className="stat-label">24h Trades</div>
            <div className="stat-value">
              <span style={{ color: '#27ae60' }}>{data.buys_24h || 0}↑</span>
              {' / '}
              <span style={{ color: '#e74c3c' }}>{data.sells_24h || 0}↓</span>
            </div>
          </div>
        )}

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
