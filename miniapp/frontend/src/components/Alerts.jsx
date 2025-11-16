import { useState, useEffect } from 'react'

function Alerts() {
  const [alerts, setAlerts] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState({
    source: 'weex_cex',
    targetPrice: '',
    direction: 'above'
  })

  useEffect(() => {
    loadAlerts()
  }, [])

  const loadAlerts = () => {
    const saved = localStorage.getItem('priceAlerts')
    if (saved) {
      setAlerts(JSON.parse(saved))
    }
  }

  const saveAlerts = (newAlerts) => {
    localStorage.setItem('priceAlerts', JSON.stringify(newAlerts))
    setAlerts(newAlerts)
  }

  const handleSubmit = (e) => {
    e.preventDefault()

    if (!formData.targetPrice || parseFloat(formData.targetPrice) <= 0) {
      alert('Please enter a valid target price')
      return
    }

    const newAlert = {
      id: Date.now(),
      source: formData.source,
      targetPrice: parseFloat(formData.targetPrice),
      direction: formData.direction,
      createdAt: new Date().toISOString(),
      triggered: false
    }

    saveAlerts([...alerts, newAlert])
    setFormData({ source: 'weex_cex', targetPrice: '', direction: 'above' })
    setShowForm(false)
  }

  const deleteAlert = (id) => {
    saveAlerts(alerts.filter(alert => alert.id !== id))
  }

  const getSourceName = (source) => {
    const names = {
      'stonfi_dex': 'DEX (TON)',
      'stonfi_dex_usdt': 'DEX (USDT)',
      'weex_cex': 'CEX'
    }
    return names[source] || source
  }

  return (
    <div>
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: '600', margin: 0 }}>Price Alerts</h2>
          <button
            className="btn-secondary"
            onClick={() => setShowForm(!showForm)}
            style={{
              width: 'auto',
              padding: '8px 16px',
              borderRadius: '10px',
              fontSize: '15px'
            }}
          >
            {showForm ? 'Cancel' : 'New Alert'}
          </button>
        </div>

        {showForm && (
          <form onSubmit={handleSubmit} style={{
            padding: '16px',
            background: 'var(--fill-quaternary)',
            borderRadius: '10px',
            marginBottom: '16px'
          }}>
            <div style={{ marginBottom: '16px' }}>
              <label style={{
                display: 'block',
                fontSize: '13px',
                color: 'var(--label-secondary)',
                marginBottom: '8px',
                fontWeight: '500'
              }}>
                Source
              </label>
              <select
                value={formData.source}
                onChange={(e) => setFormData({ ...formData, source: e.target.value })}
                style={{
                  width: '100%',
                  padding: '12px',
                  borderRadius: '10px',
                  border: 'none',
                  background: 'var(--system-secondary-background)',
                  color: 'var(--label-primary)',
                  fontSize: '17px',
                  fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif'
                }}
              >
                <option value="weex_cex">CEX</option>
                <option value="stonfi_dex">DEX (TON)</option>
                <option value="stonfi_dex_usdt">DEX (USDT)</option>
              </select>
            </div>

            <div style={{ marginBottom: '16px' }}>
              <label style={{
                display: 'block',
                fontSize: '13px',
                color: 'var(--label-secondary)',
                marginBottom: '8px',
                fontWeight: '500'
              }}>
                Target Price (USD)
              </label>
              <input
                type="number"
                step="0.000001"
                value={formData.targetPrice}
                onChange={(e) => setFormData({ ...formData, targetPrice: e.target.value })}
                placeholder="0.005000"
                style={{
                  width: '100%',
                  padding: '12px',
                  borderRadius: '10px',
                  border: 'none',
                  background: 'var(--system-secondary-background)',
                  color: 'var(--label-primary)',
                  fontSize: '17px',
                  fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif'
                }}
                required
              />
            </div>

            <div style={{ marginBottom: '16px' }}>
              <label style={{
                display: 'block',
                fontSize: '13px',
                color: 'var(--label-secondary)',
                marginBottom: '8px',
                fontWeight: '500'
              }}>
                Alert When Price Goes
              </label>
              <select
                value={formData.direction}
                onChange={(e) => setFormData({ ...formData, direction: e.target.value })}
                style={{
                  width: '100%',
                  padding: '12px',
                  borderRadius: '10px',
                  border: 'none',
                  background: 'var(--system-secondary-background)',
                  color: 'var(--label-primary)',
                  fontSize: '17px',
                  fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif'
                }}
              >
                <option value="above">Above Target</option>
                <option value="below">Below Target</option>
              </select>
            </div>

            <button
              type="submit"
              className="btn-primary"
              style={{
                marginTop: '8px',
                fontSize: '17px',
                fontWeight: '600'
              }}
            >
              Create Alert
            </button>
          </form>
        )}

        {alerts.length === 0 && !showForm && (
          <div style={{
            textAlign: 'center',
            padding: '40px 16px',
            color: 'var(--label-secondary)'
          }}>
            <p style={{ fontSize: '15px', marginBottom: '8px' }}>No alerts configured</p>
            <p style={{ fontSize: '13px' }}>Create an alert to get notified when price reaches your target</p>
          </div>
        )}

        {alerts.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {alerts.map(alert => (
              <div
                key={alert.id}
                style={{
                  padding: '16px',
                  background: 'var(--fill-quaternary)',
                  borderRadius: '10px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}
              >
                <div>
                  <div style={{
                    fontSize: '17px',
                    fontWeight: '600',
                    color: 'var(--label-primary)',
                    marginBottom: '4px'
                  }}>
                    {getSourceName(alert.source)}
                  </div>
                  <div style={{
                    fontSize: '15px',
                    color: 'var(--label-secondary)'
                  }}>
                    Alert when price goes <strong>{alert.direction}</strong> ${alert.targetPrice.toFixed(6)}
                  </div>
                  <div style={{
                    fontSize: '13px',
                    color: 'var(--label-tertiary)',
                    marginTop: '4px'
                  }}>
                    Created {new Date(alert.createdAt).toLocaleDateString()}
                  </div>
                </div>
                <button
                  onClick={() => deleteAlert(alert.id)}
                  style={{
                    padding: '8px 16px',
                    borderRadius: '10px',
                    border: 'none',
                    background: 'var(--system-red)',
                    color: '#ffffff',
                    fontSize: '15px',
                    fontWeight: '600',
                    cursor: 'pointer',
                    transition: 'opacity 0.15s ease-in-out'
                  }}
                  onMouseDown={(e) => e.currentTarget.style.opacity = '0.6'}
                  onMouseUp={(e) => e.currentTarget.style.opacity = '1'}
                  onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
                >
                  Delete
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card" style={{
        background: 'var(--fill-tertiary)',
        borderLeft: '4px solid var(--system-orange)'
      }}>
        <div style={{ fontSize: '13px', color: 'var(--label-secondary)', lineHeight: '1.5' }}>
          <strong style={{ color: 'var(--label-primary)', display: 'block', marginBottom: '8px' }}>
            Note:
          </strong>
          Alerts are stored locally in this app. To receive Telegram notifications when your target price is reached,
          please configure alerts through the bot using the /alerts command.
        </div>
      </div>
    </div>
  )
}

export default Alerts
