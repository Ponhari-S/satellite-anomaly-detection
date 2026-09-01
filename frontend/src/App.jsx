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
      setReadings((prev) => [data, ...prev].slice(0, 20))
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

  const statusColor = {
    connected: 'text-emerald-400',
    disconnected: 'text-amber-400',
    error: 'text-red-400',
    closed: 'text-slate-500',
  }[streamStatus] ?? 'text-amber-400'

  const statusDot = {
    connected: 'bg-emerald-400',
    disconnected: 'bg-amber-400',
    error: 'bg-red-400',
    closed: 'bg-slate-500',
  }[streamStatus] ?? 'bg-amber-400'

  return (
    <div className="min-h-screen bg-[#0B1220] text-slate-200 font-sans">
      <div className="max-w-6xl mx-auto px-6 py-10">

        <div className="flex items-baseline justify-between border-b border-slate-800 pb-4 mb-8">
          <div>
            <p className="text-xs uppercase tracking-widest text-slate-500 mb-1">Frontend scaffold</p>
            <h1 className="text-2xl font-semibold text-slate-100">Satellite anomaly detection</h1>
          </div>
          <div className="flex items-center gap-2">
            <span className={`h-2 w-2 rounded-full ${statusDot} ${streamStatus === 'connected' ? 'animate-pulse' : ''}`} />
            <span className={`text-sm font-mono ${statusColor}`}>{streamStatus}</span>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-10">
          <div className="rounded-lg border border-slate-800 bg-[#121B2B] p-5">
            <p className="text-xs uppercase tracking-widest text-slate-500 mb-3">Backend connectivity — day 22</p>
            {healthError && (
              <p className="text-red-400 text-sm font-mono">Error: {healthError}</p>
            )}
            {health && (
              <pre className="text-xs font-mono text-slate-300 whitespace-pre-wrap leading-relaxed">
                {JSON.stringify(health, null, 2)}
              </pre>
            )}
            {!health && !healthError && (
              <p className="text-sm text-slate-500 font-mono">Checking…</p>
            )}
          </div>

          <div className="rounded-lg border border-slate-800 bg-[#121B2B] p-5">
            <p className="text-xs uppercase tracking-widest text-slate-500 mb-3">Live telemetry — day 23</p>
            <p className="text-sm text-slate-400">
              Streaming from <span className="font-mono text-slate-300">{BACKEND_WS}</span>
            </p>
            <p className="text-sm text-slate-400 mt-1">
              Buffer: <span className="font-mono text-slate-300">{readings.length}/20</span> readings
            </p>
          </div>
        </div>

        <div className="rounded-lg border border-slate-800 overflow-hidden">
          <table className="w-full text-sm font-mono border-collapse">
            <thead>
              <tr className="bg-[#0F1826] text-slate-500 text-xs uppercase tracking-wider">
                <th className="text-left px-4 py-3 font-medium">Timestamp</th>
                <th className="text-left px-4 py-3 font-medium">Channel</th>
                <th className="text-left px-4 py-3 font-medium">Value</th>
                <th className="text-left px-4 py-3 font-medium">True label</th>
                <th className="text-left px-4 py-3 font-medium">Prediction</th>
                <th className="text-left px-4 py-3 font-medium">Probability</th>
              </tr>
            </thead>
            <tbody>
              {readings.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-slate-600">
                    Waiting for telemetry…
                  </td>
                </tr>
              )}
              {readings.map((r, i) => (
                <tr
                  key={i}
                  className={`border-t border-slate-800/70 ${
                    r.prediction === 1 ? 'bg-red-950/20' : ''
                  }`}
                >
                  <td className="px-4 py-2 text-slate-400">{r.timestamp}</td>
                  <td className="px-4 py-2 text-slate-300">{r.channel}</td>
                  <td className="px-4 py-2 text-slate-300">{Number(r.value).toExponential(3)}</td>
                  <td className="px-4 py-2 text-slate-400">
                    {r.anomaly === 1 ? 'anomaly' : 'normal'}
                  </td>
                  <td className={`px-4 py-2 font-medium ${r.prediction === 1 ? 'text-red-400' : 'text-emerald-400'}`}>
                    {r.prediction === 1 ? 'anomaly' : 'normal'}
                  </td>
                  <td className="px-4 py-2 text-slate-300">{r.probability?.toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

      </div>
    </div>
  )
}

export default App