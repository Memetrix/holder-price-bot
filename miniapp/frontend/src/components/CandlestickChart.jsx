import { useState, useEffect } from 'react'
import ReactECharts from 'echarts-for-react'

function CandlestickChart() {
  const [historyData, setHistoryData] = useState([])
  const [period, setPeriod] = useState('1h')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchHistory()
  }, [period])

  const fetchHistory = async () => {
    setLoading(true)
    try {
      let hours
      switch(period) {
        case '1m': hours = 1/60; break
        case '5m': hours = 5/60; break
        case '15m': hours = 15/60; break
        case '1h': hours = 1; break
        case '24h': hours = 24; break
        case '7d': hours = 168; break
        default: hours = 1
      }

      const response = await fetch(`/api/history?source=cex&hours=${hours}&limit=500`)
      const data = await response.json()

      if (data.success) {
        setHistoryData(data.data.reverse())
      }
    } catch (err) {
      console.error('Failed to fetch history:', err)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="card">
        <div className="loading">Loading chart data...</div>
      </div>
    )
  }

  if (!historyData || historyData.length === 0) {
    return (
      <div className="card">
        <p>No historical data available yet. The bot needs to run for some time to collect price history.</p>
      </div>
    )
  }

  // Get theme from document
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark'

  // Process data into candlestick format
  // Group by hour to create OHLC candles
  const groupedData = {}

  historyData.forEach(item => {
    const date = new Date(item.timestamp)
    const hourKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:00`

    if (!groupedData[hourKey]) {
      groupedData[hourKey] = {
        timestamp: hourKey,
        open: parseFloat(item.price_usd || item.price),
        high: parseFloat(item.high_24h || item.price),
        low: parseFloat(item.low_24h || item.price),
        close: parseFloat(item.price_usd || item.price),
        volume: parseFloat(item.volume_24h || 0),
        prices: [parseFloat(item.price_usd || item.price)]
      }
    } else {
      const price = parseFloat(item.price_usd || item.price)
      groupedData[hourKey].prices.push(price)
      groupedData[hourKey].close = price
      groupedData[hourKey].high = Math.max(groupedData[hourKey].high, parseFloat(item.high_24h || price))
      groupedData[hourKey].low = Math.min(groupedData[hourKey].low, parseFloat(item.low_24h || price))
      groupedData[hourKey].volume = Math.max(groupedData[hourKey].volume, parseFloat(item.volume_24h || 0))
    }
  })

  // Convert to arrays
  const timestamps = Object.keys(groupedData)
  const candlestickData = timestamps.map(key => {
    const candle = groupedData[key]
    return [candle.open, candle.close, candle.low, candle.high]
  })
  const volumeData = timestamps.map(key => groupedData[key].volume)

  // Format timestamps for display
  const formattedTimestamps = timestamps.map(ts => {
    const date = new Date(ts)
    if (period === '1h') {
      return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
    }
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit' })
  })

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      },
      backgroundColor: isDark ? '#2c2c2e' : '#ffffff',
      borderColor: isDark ? '#54545899' : '#3c3c4349',
      textStyle: {
        color: isDark ? '#ffffff' : '#000000',
        fontSize: 13,
        fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif'
      },
      formatter: function(params) {
        const candleData = params[0]
        if (!candleData) return ''

        const values = candleData.value
        return `
          <div style="font-weight: 600; margin-bottom: 8px;">${candleData.name}</div>
          <div style="margin: 4px 0;">Open: <strong>$${values[1].toFixed(6)}</strong></div>
          <div style="margin: 4px 0;">Close: <strong>$${values[2].toFixed(6)}</strong></div>
          <div style="margin: 4px 0;">Low: <strong>$${values[3].toFixed(6)}</strong></div>
          <div style="margin: 4px 0;">High: <strong>$${values[4].toFixed(6)}</strong></div>
          ${params[1] ? `<div style="margin: 4px 0;">Volume: <strong>${params[1].value.toFixed(0)}</strong></div>` : ''}
        `
      }
    },
    grid: [
      {
        left: '3%',
        right: '4%',
        top: '8%',
        height: '60%',
        containLabel: true
      },
      {
        left: '3%',
        right: '4%',
        top: '75%',
        height: '18%',
        containLabel: true
      }
    ],
    xAxis: [
      {
        type: 'category',
        data: formattedTimestamps,
        boundaryGap: true,
        axisLine: {
          lineStyle: {
            color: isDark ? '#54545899' : '#3c3c4349'
          }
        },
        axisLabel: {
          color: isDark ? '#ebebf560' : '#3c3c4399',
          fontSize: 11,
          fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif',
          rotate: 45,
          interval: Math.floor(formattedTimestamps.length / 6)
        },
        splitLine: {
          show: false
        }
      },
      {
        type: 'category',
        gridIndex: 1,
        data: formattedTimestamps,
        boundaryGap: true,
        axisLine: {
          show: false
        },
        axisLabel: {
          show: false
        },
        splitLine: {
          show: false
        }
      }
    ],
    yAxis: [
      {
        scale: true,
        axisLabel: {
          formatter: '${value}',
          color: isDark ? '#ebebf560' : '#3c3c4399',
          fontSize: 11,
          fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif'
        },
        axisLine: {
          show: false
        },
        splitLine: {
          lineStyle: {
            color: isDark ? '#54545899' : '#3c3c4349',
            type: 'dashed'
          }
        }
      },
      {
        scale: true,
        gridIndex: 1,
        axisLabel: {
          show: false
        },
        axisLine: {
          show: false
        },
        splitLine: {
          show: false
        }
      }
    ],
    series: [
      {
        name: 'Price',
        type: 'candlestick',
        data: candlestickData,
        itemStyle: {
          color: isDark ? '#30d158' : '#34c759',
          color0: isDark ? '#ff453a' : '#ff3b30',
          borderColor: isDark ? '#30d158' : '#34c759',
          borderColor0: isDark ? '#ff453a' : '#ff3b30'
        }
      },
      {
        name: 'Volume',
        type: 'bar',
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: volumeData,
        itemStyle: {
          color: function(params) {
            const candle = candlestickData[params.dataIndex]
            if (!candle) return isDark ? '#0a84ff' : '#007aff'
            // Green if close >= open, red otherwise
            return candle[1] >= candle[0]
              ? (isDark ? '#30d15880' : '#34c75980')
              : (isDark ? '#ff453a80' : '#ff3b3080')
          }
        }
      }
    ]
  }

  return (
    <div className="card">
      <div className="card-title">Candlestick Chart</div>

      <div className="tabs" style={{ marginBottom: '16px' }}>
        <button
          className={`tab ${period === '1m' ? 'active' : ''}`}
          onClick={() => setPeriod('1m')}
        >
          1m
        </button>
        <button
          className={`tab ${period === '5m' ? 'active' : ''}`}
          onClick={() => setPeriod('5m')}
        >
          5m
        </button>
        <button
          className={`tab ${period === '15m' ? 'active' : ''}`}
          onClick={() => setPeriod('15m')}
        >
          15m
        </button>
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

      <div style={{ height: '500px', width: '100%' }}>
        <ReactECharts
          option={option}
          style={{ height: '100%', width: '100%' }}
          opts={{ renderer: 'canvas' }}
        />
      </div>
    </div>
  )
}

export default CandlestickChart
