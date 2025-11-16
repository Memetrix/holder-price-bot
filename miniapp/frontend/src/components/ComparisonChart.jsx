import { useState, useEffect } from 'react'
import ReactECharts from 'echarts-for-react'

function ComparisonChart() {
  const [historyData, setHistoryData] = useState({
    dex_ton: [],
    dex_usdt: [],
    cex: []
  })
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
        case '1m': hours = 1/60; break  // 1 minute = 0.0167 hours
        case '5m': hours = 5/60; break  // 5 minutes = 0.083 hours
        case '15m': hours = 15/60; break // 15 minutes = 0.25 hours
        case '1h': hours = 1; break
        case '24h': hours = 24; break
        case '7d': hours = 168; break
        default: hours = 1
      }

      // Fetch all three sources in parallel
      const [dexTonRes, dexUsdtRes, cexRes] = await Promise.all([
        fetch(`/api/history?source=dex_ton&hours=${hours}&limit=500`),
        fetch(`/api/history?source=dex_usdt&hours=${hours}&limit=500`),
        fetch(`/api/history?source=cex&hours=${hours}&limit=500`)
      ])

      const [dexTonData, dexUsdtData, cexData] = await Promise.all([
        dexTonRes.json(),
        dexUsdtRes.json(),
        cexRes.json()
      ])

      setHistoryData({
        dex_ton: dexTonData.success ? dexTonData.data.reverse() : [],
        dex_usdt: dexUsdtData.success ? dexUsdtData.data.reverse() : [],
        cex: cexData.success ? cexData.data.reverse() : []
      })
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

  if (!historyData.dex_ton.length && !historyData.dex_usdt.length && !historyData.cex.length) {
    return (
      <div className="card">
        <p>No historical data available yet. The bot needs to run for some time to collect price history.</p>
      </div>
    )
  }

  // Get theme from document
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark'

  // Prepare data for chart
  const timestamps = historyData.cex.map(item => {
    const date = new Date(item.timestamp)
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
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
        let result = `<div style="font-weight: 600; margin-bottom: 8px;">${params[0].axisValue}</div>`
        params.forEach(param => {
          result += `<div style="margin: 4px 0;">
            <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: ${param.color}; margin-right: 8px;"></span>
            ${param.seriesName}: <strong>$${param.value.toFixed(6)}</strong>
          </div>`
        })
        return result
      }
    },
    legend: {
      data: ['DEX (TON)', 'DEX (USDT)', 'CEX'],
      textStyle: {
        color: isDark ? '#ebebf599' : '#3c3c43',
        fontSize: 13,
        fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif'
      },
      top: 10,
      left: 'center'
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '20%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: timestamps,
      axisLabel: {
        color: isDark ? '#ebebf560' : '#3c3c4399',
        fontSize: 11,
        fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif',
        rotate: 45,
        interval: Math.floor(timestamps.length / 6)
      },
      axisLine: {
        lineStyle: {
          color: isDark ? '#54545899' : '#3c3c4349'
        }
      },
      splitLine: {
        show: false
      }
    },
    yAxis: {
      type: 'value',
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
    series: [
      {
        name: 'DEX (TON)',
        type: 'line',
        data: historyData.dex_ton.map(item => parseFloat(item.price_usd || item.price)),
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: {
          width: 2,
          color: '#34c759'
        },
        itemStyle: {
          color: '#34c759'
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [{
              offset: 0, color: 'rgba(52, 199, 89, 0.3)'
            }, {
              offset: 1, color: 'rgba(52, 199, 89, 0.05)'
            }]
          }
        }
      },
      {
        name: 'DEX (USDT)',
        type: 'line',
        data: historyData.dex_usdt.map(item => parseFloat(item.price_usd || item.price)),
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: {
          width: 2,
          color: '#30d158'
        },
        itemStyle: {
          color: '#30d158'
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [{
              offset: 0, color: 'rgba(48, 209, 88, 0.2)'
            }, {
              offset: 1, color: 'rgba(48, 209, 88, 0.02)'
            }]
          }
        }
      },
      {
        name: 'CEX',
        type: 'line',
        data: historyData.cex.map(item => parseFloat(item.price_usd || item.price)),
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: {
          width: 2,
          color: '#0a84ff'
        },
        itemStyle: {
          color: '#0a84ff'
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [{
              offset: 0, color: 'rgba(10, 132, 255, 0.2)'
            }, {
              offset: 1, color: 'rgba(10, 132, 255, 0.02)'
            }]
          }
        }
      }
    ]
  }

  return (
    <div className="card">
      <div className="card-title">Price Comparison</div>

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

      <div style={{ height: '400px', width: '100%' }}>
        <ReactECharts
          option={option}
          style={{ height: '100%', width: '100%' }}
          opts={{ renderer: 'canvas' }}
        />
      </div>
    </div>
  )
}

export default ComparisonChart
