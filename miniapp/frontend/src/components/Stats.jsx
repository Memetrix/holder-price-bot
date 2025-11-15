function Stats({ data }) {
  const formatPrice = (price) => {
    if (!price) return 'N/A'
    return parseFloat(price).toFixed(6)
  }

  const formatChange = (change) => {
    if (!change) return 'N/A'
    return parseFloat(change).toFixed(2)
  }

  return (
    <div>
      {data.dex && (
        <div className="card">
          <div className="card-title" style={{ color: '#27ae60' }}>
            🟢 DEX Statistics (24h)
          </div>

          <div className="stats-grid">
            <div className="stat-item">
              <div className="stat-label">Current Price</div>
              <div className="stat-value">${formatPrice(data.dex.current)}</div>
            </div>

            <div className="stat-item">
              <div className="stat-label">24h Change</div>
              <div className="stat-value" style={{
                color: data.dex.change >= 0 ? '#27ae60' : '#e74c3c'
              }}>
                {formatChange(data.dex.change)}%
              </div>
            </div>

            <div className="stat-item">
              <div className="stat-label">24h High</div>
              <div className="stat-value">${formatPrice(data.dex.high)}</div>
            </div>

            <div className="stat-item">
              <div className="stat-label">24h Low</div>
              <div className="stat-value">${formatPrice(data.dex.low)}</div>
            </div>

            <div className="stat-item" style={{ gridColumn: '1 / -1' }}>
              <div className="stat-label">24h Volume</div>
              <div className="stat-value">
                ${data.dex.volume ? parseFloat(data.dex.volume).toLocaleString() : 'N/A'}
              </div>
            </div>
          </div>
        </div>
      )}

      {data.cex && (
        <div className="card">
          <div className="card-title" style={{ color: '#3498db' }}>
            🔵 CEX Statistics (24h)
          </div>

          <div className="stats-grid">
            <div className="stat-item">
              <div className="stat-label">Current Price</div>
              <div className="stat-value">${formatPrice(data.cex.current)}</div>
            </div>

            <div className="stat-item">
              <div className="stat-label">24h Change</div>
              <div className="stat-value" style={{
                color: data.cex.change >= 0 ? '#27ae60' : '#e74c3c'
              }}>
                {formatChange(data.cex.change)}%
              </div>
            </div>

            <div className="stat-item">
              <div className="stat-label">24h High</div>
              <div className="stat-value">${formatPrice(data.cex.high)}</div>
            </div>

            <div className="stat-item">
              <div className="stat-label">24h Low</div>
              <div className="stat-value">${formatPrice(data.cex.low)}</div>
            </div>

            <div className="stat-item" style={{ gridColumn: '1 / -1' }}>
              <div className="stat-label">24h Volume</div>
              <div className="stat-value">
                ${data.cex.volume ? parseFloat(data.cex.volume).toLocaleString() : 'N/A'}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Stats
