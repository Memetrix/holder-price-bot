import { useState, useEffect } from 'react'
import PriceCard from './components/PriceCard'
import Chart from './components/Chart'
import Stats from './components/Stats'
import Arbitrage from './components/Arbitrage'

function App() {
  const [prices, setPrices] = useState(null)
  const [stats, setStats] = useState(null)
  const [arbitrage, setArbitrage] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('price')
  const [ws, setWs] = useState(null)

  // Initialize Telegram WebApp
  useEffect(() => {
    if (window.Telegram?.WebApp) {
      const tg = window.Telegram.WebApp
      tg.ready()
      tg.expand()

      // Set theme colors
      document.documentElement.style.setProperty('--tg-theme-bg-color', tg.backgroundColor)
      document.documentElement.style.setProperty('--tg-theme-text-color', tg.textColor)
      document.documentElement.style.setProperty('--tg-theme-button-color', tg.buttonColor)
      document.documentElement.style.setProperty('--tg-theme-button-text-color', tg.buttonTextColor)
    }
  }, [])

  // Fetch initial data
  useEffect(() => {
    fetchPriceData()
    fetchStats()
    fetchArbitrage()
  }, [])

  // WebSocket connection
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws`

    const websocket = new WebSocket(wsUrl)

    websocket.onopen = () => {
      console.log('WebSocket connected')
    }

    websocket.onmessage = (event) => {
      const message = JSON.parse(event.data)

      if (message.type === 'price_update' || message.type === 'initial_data') {
        setPrices(message.data)
      }
    }

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    websocket.onclose = () => {
      console.log('WebSocket disconnected')
      // Attempt to reconnect after 5 seconds
      setTimeout(() => {
        fetchPriceData()
      }, 5000)
    }

    setWs(websocket)

    return () => {
      if (websocket) {
        websocket.close()
      }
    }
  }, [])

  const fetchPriceData = async () => {
    try {
      const response = await fetch('/api/price')
      const data = await response.json()

      if (data.success) {
        setPrices(data.data)
      } else {
        setError('Failed to fetch price data')
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const fetchStats = async () => {
    try {
      const response = await fetch('/api/stats')
      const data = await response.json()

      if (data.success) {
        setStats(data.data)
      }
    } catch (err) {
      console.error('Failed to fetch stats:', err)
    }
  }

  const fetchArbitrage = async () => {
    try {
      const response = await fetch('/api/arbitrage')
      const data = await response.json()

      if (data.success && data.has_opportunity) {
        setArbitrage(data.data)
      } else {
        setArbitrage(null)
      }
    } catch (err) {
      console.error('Failed to fetch arbitrage data:', err)
    }
  }

  const handleRefresh = () => {
    setLoading(true)
    fetchPriceData()
    fetchStats()
    fetchArbitrage()
  }

  if (loading) {
    return (
      <div className="container">
        <div className="loading">
          <p>Loading HOLDER prices...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="container">
        <div className="error">
          <p>Error: {error}</p>
          <button className="btn btn-primary" onClick={handleRefresh}>
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="container">
      <h1 style={{ marginBottom: '20px', fontSize: '24px', fontWeight: '700' }}>
        💰 HOLDER Price Monitor
      </h1>

      {arbitrage && <Arbitrage data={arbitrage} />}

      <div className="tabs">
        <button
          className={`tab ${activeTab === 'price' ? 'active' : ''}`}
          onClick={() => setActiveTab('price')}
        >
          📊 Prices
        </button>
        <button
          className={`tab ${activeTab === 'chart' ? 'active' : ''}`}
          onClick={() => setActiveTab('chart')}
        >
          📈 Charts
        </button>
        <button
          className={`tab ${activeTab === 'stats' ? 'active' : ''}`}
          onClick={() => setActiveTab('stats')}
        >
          📉 Stats
        </button>
      </div>

      {activeTab === 'price' && prices && (
        <div>
          {prices.dex && (
            <PriceCard
              title="STON.fi DEX"
              source="DEX"
              data={prices.dex}
              color="#27ae60"
            />
          )}

          {prices.cex && (
            <PriceCard
              title="WEEX CEX"
              source="CEX"
              data={prices.cex}
              color="#3498db"
            />
          )}
        </div>
      )}

      {activeTab === 'chart' && <Chart />}

      {activeTab === 'stats' && stats && <Stats data={stats} />}

      <button
        className="btn btn-primary"
        onClick={handleRefresh}
        style={{ marginTop: '16px' }}
      >
        🔄 Refresh Data
      </button>

      <div style={{
        textAlign: 'center',
        marginTop: '20px',
        fontSize: '12px',
        color: 'var(--tg-theme-hint-color)'
      }}>
        Last updated: {new Date().toLocaleTimeString()}
      </div>
    </div>
  )
}

export default App
