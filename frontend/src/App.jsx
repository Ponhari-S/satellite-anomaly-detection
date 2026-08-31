import { useState, useEffect, useRef } from 'react'

const BACKEND_HTTP = 'http://127.0.0.1:8000'
const BACKEND_WS = 'ws://127.0.0.1:8000/stream'

function App() {
  const [health, setHealth] = useState(null)
  const [healthError, setHealthError] = useState(null)

  const [streamStatus, setStreamStatus] = useState('disconnected')
  const [readings, setReadings] = useState([])
  const wsRef = useRef(null)

  useEffect(() => {
    fetch(`${BACKEND_HTTP}/health`)
      .then((res) => res.json())
      .then((data) => setHealth(data))
      .catch((err) => setHealthError(err.message))
  }, [])

  useEffect(() => {
    const ws = new WebSocket(BACKEND_WS)
    wsRef.current = ws

    ws.onopen = () => {
      setStreamStatus('connected')
      console.log('[stream] connected to', BACKEND_WS)
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      console.log('[stream] reading received:', data)
      setReadings((prev) => [data, ...prev].slice(0, 20)) // keep last 20
    }

    ws.onerror = (err) => {
      console.error('[stream] error:', err)
      setStreamStatus('error')
    }

    ws.onclose = () => {
      console.log('[stream] connection closed')
      setStreamStatus('closed')
    }

    return () => ws.close()
  }, [])

  return (
    <div style={{ padding: '2rem', fontFamily: 'sans-serif' }}>
      <h1>Satellite Anomaly Detection — Frontend Scaffold</h1>

      <h2>Backend connectivity check (Day 22)</h2>
      {healthError && <p style={{ color: 'red' }}>Error: {healthError}</p>}
      {health && <pre>{JSON.stringify(health, null, 2)}</pre>}

      <h2>Live telemetry stream (Day 23)</h2>
      <p>
        Status:{' '}
        <strong style={{ color: streamStatus === 'connected' ? 'green' : 'orange' }}>
          {streamStatus}
        </strong>
      </p>

      <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: '13px' }}>
        <thead>
          <tr>
            <th style={cellStyle}>Timestamp</th>
            <th style={cellStyle}>Channel</th>
            <th style={cellStyle}>Value</th>
            <th style={cellStyle}>True label</th>
            <th style={cellStyle}>Prediction</th>
            <th style={cellStyle}>Probability</th>
          </tr>
        </thead>
        <tbody>
          {readings.map((r, i) => (
            <tr key={i}>
              <td style={cellStyle}>{r.timestamp}</td>
              <td style={cellStyle}>{r.channel}</td>
              <td style={cellStyle}>{Number(r.value).toExponential(3)}</td>
              <td style={cellStyle}>{r.anomaly === 1 ? 'anomaly' : 'normal'}</td>
              <td style={{ ...cellStyle, color: r.prediction === 1 ? 'red' : 'green' }}>
                {r.prediction === 1 ? 'anomaly' : 'normal'}
              </td>
              <td style={cellStyle}>{r.probability?.toFixed(3)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

const cellStyle = {
  border: '1px solid #333',
  padding: '4px 8px',
  textAlign: 'left',
}

export default App