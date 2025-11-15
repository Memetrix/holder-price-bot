import { useState, useEffect } from 'react'
import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

function Chart() {
  const [history, setHistory] = useState([])
  const [period, setPeriod] = useState('24h')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchHistory()
  }, [period])

  const fetchHistory = async () => {
    setLoading(true)
    try {
      const hours = period === '1h' ? 1 : period === '7d' ? 168 : 24
      const response = await fetch(`/api/history?source=weex_cex&hours=${hours}&limit=500`)
      const data = await response.json()

      if (data.success) {
        setHistory(data.data.reverse())
      }
    } catch (err) {
      console.error('Failed to fetch history:', err)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="card"><div className="loading">Loading chart...</div></div>
  }

  if (!history || history.length === 0) {
    return (
      <div className="card">
        <p>No historical data available yet. The bot needs to run for some time to collect price history.</p>
      </div>
    )
  }

  const chartData = {
    labels: history.map(item => {
      const date = new Date(item.timestamp)
      return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
    }),
    datasets: [
      {
        label: 'HOLDER Price (USDT)',
        data: history.map(item => parseFloat(item.price_usd || item.price)),
        borderColor: '#3498db',
        backgroundColor: 'rgba(52, 152, 219, 0.1)',
        fill: true,
        tension: 0.4,
      }
    ]
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false
      },
      tooltip: {
        mode: 'index',
        intersect: false,
        callbacks: {
          label: function(context) {
            return `$${context.parsed.y.toFixed(6)}`
          }
        }
      }
    },
    scales: {
      x: {
        display: true,
        ticks: {
          maxTicksLimit: 6
        }
      },
      y: {
        display: true,
        ticks: {
          callback: function(value) {
            return '$' + value.toFixed(6)
          }
        }
      }
    }
  }

  return (
    <div className="card">
      <div className="card-title">Price History</div>

      <div className="tabs" style={{ marginBottom: '16px' }}>
        <button
          className={`tab ${period === '1h' ? 'active' : ''}`}
          onClick={() => setPeriod('1h')}
        >
          1h
        </button>
        <button
          className={`tab ${period === '24h' ? 'active' : ''}`}
          onClick={() => setPeriod('24h')}
        >
          24h
        </button>
        <button
          className={`tab ${period === '7d' ? 'active' : ''}`}
          onClick={() => setPeriod('7d')}
        >
          7d
        </button>
      </div>

      <div className="chart-container">
        <Line data={chartData} options={options} />
      </div>
    </div>
  )
}

export default Chart
