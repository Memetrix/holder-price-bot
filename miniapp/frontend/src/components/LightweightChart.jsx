import { useState, useEffect, useRef } from 'react'
import { createChart, ColorType, CrosshairMode, CandlestickSeries, HistogramSeries } from 'lightweight-charts'

function LightweightChart() {
  const [historyData, setHistoryData] = useState({ dex_ton: [], dex_usdt: [], cex: [] })
  const [period, setPeriod] = useState('24h')
  const [loading, setLoading] = useState(true)
  const [source, setSource] = useState('all') // 'all', 'dex_ton', 'dex_usdt', 'cex'

  const chartContainerRef = useRef()
  const chartRef = useRef()
  const candlestickSeriesRef = useRef()
  const volumeSeriesRef = useRef()

  useEffect(() => {
    fetchHistory()
  }, [period])

  useEffect(() => {
    if (!chartContainerRef.current || historyData.cex.length === 0) return

    // Get theme
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark'

    // Create chart
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 500,
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: isDark ? '#ebebf599' : '#3c3c4399',
        fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif',
      },
      grid: {
        vertLines: {
          color: isDark ? '#54545820' : '#3c3c4320',
        },
        horzLines: {
          color: isDark ? '#54545820' : '#3c3c4320',
        },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: {
          color: isDark ? '#0a84ff' : '#007aff',
          width: 1,
          style: 3,
          labelBackgroundColor: isDark ? '#0a84ff' : '#007aff',
        },
        horzLine: {
          color: isDark ? '#0a84ff' : '#007aff',
          width: 1,
          style: 3,
          labelBackgroundColor: isDark ? '#0a84ff' : '#007aff',
        },
      },
      rightPriceScale: {
        borderColor: isDark ? '#54545899' : '#3c3c4349',
        scaleMargins: {
          top: 0.1,
          bottom: 0.25,
        },
      },
      timeScale: {
        borderColor: isDark ? '#54545899' : '#3c3c4349',
        timeVisible: true,
        secondsVisible: false,
      },
      handleScroll: {
        mouseWheel: true,
        pressedMouseMove: true,
        horzTouchDrag: true,
        vertTouchDrag: true,
      },
      handleScale: {
        axisPressedMouseMove: true,
        mouseWheel: true,
        pinch: true,
      },
    })

    chartRef.current = chart

    // Add candlestick series
    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: isDark ? '#30d158' : '#34c759',
      downColor: isDark ? '#ff453a' : '#ff3b30',
      borderUpColor: isDark ? '#30d158' : '#34c759',
      borderDownColor: isDark ? '#ff453a' : '#ff3b30',
      wickUpColor: isDark ? '#30d158' : '#34c759',
      wickDownColor: isDark ? '#ff453a' : '#ff3b30',
      priceFormat: {
        type: 'price',
        precision: 6,
        minMove: 0.000001,
      },
    })

    candlestickSeriesRef.current = candlestickSeries

    // Add volume series
    const volumeSeries = chart.addSeries(HistogramSeries, {
      color: isDark ? '#0a84ff80' : '#007aff80',
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: '',
      scaleMargins: {
        top: 0.8,
        bottom: 0,
      },
    })

    volumeSeriesRef.current = volumeSeries

    // Process data
    updateChartData()

    // Handle resize
    const handleResize = () => {
      if (chart && chartContainerRef.current) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth,
        })
      }
    }

    window.addEventListener('resize', handleResize)

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
    }
  }, [historyData, source, period])

  const updateChartData = () => {
    if (!candlestickSeriesRef.current || !volumeSeriesRef.current) return

    let dataToUse = []

    // Select data based on source
    switch(source) {
      case 'dex_ton':
        dataToUse = historyData.dex_ton
        break
      case 'dex_usdt':
        dataToUse = historyData.dex_usdt
        break
      case 'cex':
        dataToUse = historyData.cex
        break
      case 'all':
      default:
        // Use CEX data as primary for candlesticks
        dataToUse = historyData.cex
        break
    }

    if (dataToUse.length === 0) return

    // Dynamic interval based on selected period (like TradingView)
    const groupedData = {}
    let intervalMinutes
    switch(period) {
      case '1h':
        intervalMinutes = 5  // 5-minute candles for 1h view
        break
      case '24h':
        intervalMinutes = 60  // 1-hour candles for 24h view
        break
      case '7d':
        intervalMinutes = 240  // 4-hour candles for 7d view
        break
      default:
        intervalMinutes = 60
    }

    dataToUse.forEach(item => {
      const date = new Date(item.timestamp)

      // Round to interval (handle both minutes and hours)
      if (intervalMinutes >= 60) {
        // For intervals >= 1 hour, round by hours
        const intervalHours = intervalMinutes / 60
        const hours = Math.floor(date.getHours() / intervalHours) * intervalHours
        date.setHours(hours, 0, 0, 0)
      } else {
        // For intervals < 1 hour, round by minutes
        const minutes = Math.floor(date.getMinutes() / intervalMinutes) * intervalMinutes
        date.setMinutes(minutes, 0, 0, 0)
      }

      const timeKey = Math.floor(date.getTime() / 1000)

      const price = parseFloat(item.price_usd || item.price)

      if (!groupedData[timeKey]) {
        groupedData[timeKey] = {
          time: timeKey,
          open: price,
          high: price,
          low: price,
          close: price,
          volume: parseFloat(item.volume_24h || 0),
        }
      } else {
        groupedData[timeKey].high = Math.max(groupedData[timeKey].high, price)
        groupedData[timeKey].low = Math.min(groupedData[timeKey].low, price)
        groupedData[timeKey].close = price
        groupedData[timeKey].volume = Math.max(groupedData[timeKey].volume, parseFloat(item.volume_24h || 0))
      }
    })

    // Convert to arrays and sort by time
    const candlestickData = Object.values(groupedData).sort((a, b) => a.time - b.time)
    const volumeData = candlestickData.map(d => ({
      time: d.time,
      value: d.volume,
      color: d.close >= d.open
        ? (document.documentElement.getAttribute('data-theme') === 'dark' ? '#30d15880' : '#34c75980')
        : (document.documentElement.getAttribute('data-theme') === 'dark' ? '#ff453a80' : '#ff3b3080')
    }))

    // Update series
    candlestickSeriesRef.current.setData(candlestickData)
    volumeSeriesRef.current.setData(volumeData)

    // Fit content
    if (chartRef.current) {
      chartRef.current.timeScale().fitContent()
    }
  }

  const fetchHistory = async () => {
    setLoading(true)
    try {
      let hours
      switch(period) {
        case '1h': hours = 1; break
        case '24h': hours = 24; break
        case '7d': hours = 168; break
        default: hours = 24
      }

      // Fetch all sources (try both old and new source names for compatibility)
      const [dexTonRes, dexUsdtRes, cexRes, dexTonOldRes, dexUsdtOldRes, cexOldRes] = await Promise.all([
        fetch(`/api/history?source=stonfi_dex&hours=${hours}&limit=1000`),
        fetch(`/api/history?source=stonfi_dex_usdt&hours=${hours}&limit=1000`),
        fetch(`/api/history?source=weex_cex&hours=${hours}&limit=1000`),
        fetch(`/api/history?source=dex_ton&hours=${hours}&limit=1000`),
        fetch(`/api/history?source=dex_usdt&hours=${hours}&limit=1000`),
        fetch(`/api/history?source=cex&hours=${hours}&limit=1000`)
      ])

      const [dexTonData, dexUsdtData, cexData, dexTonOldData, dexUsdtOldData, cexOldData] = await Promise.all([
        dexTonRes.json(),
        dexUsdtRes.json(),
        cexRes.json(),
        dexTonOldRes.json(),
        dexUsdtOldRes.json(),
        cexOldRes.json()
      ])

      // Merge old and new source data
      const mergeDexTon = [
        ...(dexTonData.success ? dexTonData.data : []),
        ...(dexTonOldData.success ? dexTonOldData.data : [])
      ].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))

      const mergeDexUsdt = [
        ...(dexUsdtData.success ? dexUsdtData.data : []),
        ...(dexUsdtOldData.success ? dexUsdtOldData.data : [])
      ].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))

      const mergeCex = [
        ...(cexData.success ? cexData.data : []),
        ...(cexOldData.success ? cexOldData.data : [])
      ].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))

      setHistoryData({
        dex_ton: mergeDexTon,
        dex_usdt: mergeDexUsdt,
        cex: mergeCex
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
        <div className="loading">Loading TradingView chart...</div>
      </div>
    )
  }

  const hasData = historyData.dex_ton.length > 0 || historyData.dex_usdt.length > 0 || historyData.cex.length > 0

  if (!hasData) {
    return (
      <div className="card">
        <p>No historical data available yet. The bot needs to run for some time to collect price history.</p>
      </div>
    )
  }

  return (
    <div className="card">
      <div className="card-title">📊 HOLDER Price Chart (TradingView)</div>

      {/* Source selector */}
      <div className="tabs" style={{ marginBottom: '12px' }}>
        <button
          className={`tab ${source === 'all' ? 'active' : ''}`}
          onClick={() => setSource('all')}
        >
          All Sources
        </button>
        <button
          className={`tab ${source === 'dex_ton' ? 'active' : ''}`}
          onClick={() => setSource('dex_ton')}
          disabled={historyData.dex_ton.length === 0}
        >
          🟢 DEX TON
        </button>
        <button
          className={`tab ${source === 'dex_usdt' ? 'active' : ''}`}
          onClick={() => setSource('dex_usdt')}
          disabled={historyData.dex_usdt.length === 0}
        >
          🟢 DEX USDT
        </button>
        <button
          className={`tab ${source === 'cex' ? 'active' : ''}`}
          onClick={() => setSource('cex')}
          disabled={historyData.cex.length === 0}
        >
          🔵 CEX
        </button>
      </div>

      {/* Period selector */}
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

      {/* Chart container */}
      <div
        ref={chartContainerRef}
        style={{
          width: '100%',
          height: '500px',
          position: 'relative',
          borderRadius: '12px',
          overflow: 'hidden'
        }}
      />

      <div style={{
        marginTop: '12px',
        fontSize: '12px',
        color: 'var(--tg-theme-hint-color)',
        textAlign: 'center'
      }}>
        💡 Drag to pan • Scroll to zoom • Pinch to zoom on mobile
      </div>
    </div>
  )
}

export default LightweightChart
