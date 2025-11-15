function Arbitrage({ data }) {
  if (!data) return null

  return (
    <div className="arbitrage-alert">
      <h3>💹 Arbitrage Opportunity!</h3>

      <div className="arbitrage-details">
        <div>
          <div style={{ fontSize: '14px', opacity: 0.9 }}>
            Buy on {data.buy_on} → Sell on {data.sell_on}
          </div>
          <div style={{ fontSize: '12px', opacity: 0.8, marginTop: '4px' }}>
            Buy: ${parseFloat(data.buy_price).toFixed(6)} |
            Sell: ${parseFloat(data.sell_price).toFixed(6)}
          </div>
        </div>

        <div className="arbitrage-profit">
          +{parseFloat(data.profit_percent).toFixed(2)}%
        </div>
      </div>

      <div style={{
        marginTop: '12px',
        fontSize: '12px',
        opacity: 0.8,
        borderTop: '1px solid rgba(255,255,255,0.2)',
        paddingTop: '8px'
      }}>
        ⚠️ Remember to account for transaction fees and slippage!
      </div>
    </div>
  )
}

export default Arbitrage
