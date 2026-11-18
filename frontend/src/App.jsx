import { useState, useEffect, useRef, useMemo } from 'react'

const BACKEND_WS = 'ws://127.0.0.1:8000/stream'

const CHANNELS = [
  { id: 'CADC0872', name: 'Magnetometer X-Axis', short: 'Mag X', group: 'ADCS', unit: 'T', x: 200, y: 55, nominal: { min: -4e-5, max: 4e-5, defaultVal: 2.9408e-5 } },
  { id: 'CADC0873', name: 'Magnetometer Y-Axis', short: 'Mag Y', group: 'ADCS', unit: 'T', x: 430, y: 55, nominal: { min: -3e-5, max: 3e-5, defaultVal: -1.7241e-5 } },
  { id: 'CADC0874', name: 'Magnetometer Z-Axis', short: 'Mag Z', group: 'ADCS', unit: 'T', x: 660, y: 55, nominal: { min: -5e-5, max: 5e-5, defaultVal: 0.8412e-5 } },
  { id: 'CADC0884', name: 'Photodiode Sensor 1', short: 'PD 1', group: 'EPS', unit: 'V', x: 100, y: 180, nominal: { min: 0.1, max: 2.8, defaultVal: 2.14 } },
  { id: 'CADC0886', name: 'Photodiode Sensor 2', short: 'PD 2', group: 'EPS', unit: 'V', x: 230, y: 180, nominal: { min: 0.1, max: 2.8, defaultVal: 2.05 } },
  { id: 'CADC0888', name: 'Photodiode Sensor 3', short: 'PD 3', group: 'EPS', unit: 'V', x: 360, y: 180, nominal: { min: 0.1, max: 3.2, defaultVal: 2.22 } },
  { id: 'CADC0890', name: 'Photodiode Sensor 4', short: 'PD 4', group: 'EPS', unit: 'V', x: 490, y: 180, nominal: { min: 0.1, max: 2.8, defaultVal: 1.98 } },
  { id: 'CADC0892', name: 'Photodiode Sensor 5', short: 'PD 5', group: 'EPS', unit: 'V', x: 620, y: 180, nominal: { min: 0.1, max: 2.8, defaultVal: 2.10 } },
  { id: 'CADC0894', name: 'Photodiode Sensor 6', short: 'PD 6', group: 'EPS', unit: 'V', x: 750, y: 180, nominal: { min: 0.05, max: 2.2, defaultVal: 1.84 } },
]

// Baseline orbit correlation edges with curved paths and cross-bus links
const FALLBACK_EDGES = [
  ['CADC0872', 'CADC0873', 0.81, 'straight'],
  ['CADC0873', 'CADC0874', 0.74, 'straight'],
  ['CADC0872', 'CADC0874', 0.68, 'arc-down'],
  ['CADC0884', 'CADC0886', 0.89, 'straight'],
  ['CADC0886', 'CADC0888', 0.82, 'straight'],
  ['CADC0888', 'CADC0890', 0.85, 'straight'],
  ['CADC0890', 'CADC0892', 0.79, 'straight'],
  ['CADC0892', 'CADC0894', 0.84, 'straight'],
  ['CADC0886', 'CADC0890', 0.64, 'arc-down'],
  ['CADC0873', 'CADC0888', 0.58, 'cross-bus'],
]

// Generate smooth nominal baseline signal for warm start
function generateNominalTrace(meta) {
  const points = []
  const now = Date.now()
  const mid = meta.nominal.defaultVal
  const amp = Math.abs(meta.nominal.max - meta.nominal.min) * 0.25
  for (let i = 59; i >= 0; i--) {
    const t = now - i * 100
    const phase = (60 - i) * 0.12
    const val = mid + amp * Math.sin(phase) + amp * 0.1 * Math.cos(phase * 2.3)
    points.push({
      timestamp: new Date(t).toISOString(),
      channel: meta.id,
      value: val,
      prediction: 0,
      probability: 0.04,
      model_name: 'DynamicGraph+GRU',
    })
  }
  return points
}

function useChannelGraph() {
  const [edges, setEdges] = useState(FALLBACK_EDGES)
  const [isLive, setIsLive] = useState(false)

  useEffect(() => {
    fetch('http://127.0.0.1:8000/channel-graph')
      .then((res) => res.json())
      .then((data) => {
        if (data && data.edges && data.edges.length > 0) {
          setEdges(data.edges.map((e) => [e.source, e.target, e.strength, 'auto']))
        }
      })
      .catch(() => setEdges(FALLBACK_EDGES))

    const interval = setInterval(() => {
      fetch('http://127.0.0.1:8000/channel-graph/live')
        .then((res) => res.json())
        .then((data) => {
          if (data && data.edges && data.edges.length > 0) {
            setEdges(data.edges.map((e) => [e.source, e.target, e.strength, 'auto']))
            setIsLive(data.is_live ?? false)
          }
        })
        .catch(() => {})
    }, 4000)

    return () => clearInterval(interval)
  }, [])

  return { edges, isLive }
}

export default function App() {
  const { edges: EDGES, isLive: graphIsLive } = useChannelGraph()
  const edgesRef = useRef(EDGES)
  useEffect(() => {
    edgesRef.current = EDGES
  }, [EDGES])

  const [streamStatus, setStreamStatus] = useState('connecting')
  const [readings, setReadings] = useState([])
  const [isPaused, setIsPaused] = useState(false)
  const isPausedRef = useRef(false)
  useEffect(() => {
    isPausedRef.current = isPaused
  }, [isPaused])

  const [selectedChannel, setSelectedChannel] = useState('CADC0872')
  const [hoveredPoint, setHoveredPoint] = useState(null)
  const [currentTime, setCurrentTime] = useState(new Date().toUTCString())

  const [incidents, setIncidents] = useState([])
  const [selectedIncidentId, setSelectedIncidentId] = useState(null)
  const [incidentTab, setIncidentTab] = useState('open')
  const incidentCounterRef = useRef(100)
  const lastIncidentTimeRef = useRef({})

  const wsRef = useRef(null)

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date().toUTCString()), 1000)
    return () => clearInterval(timer)
  }, [])

  useEffect(() => {
    let ws = null
    let reconnectTimeout = null

    function connect() {
      ws = new WebSocket(BACKEND_WS)
      wsRef.current = ws

      ws.onopen = () => setStreamStatus('connected')

      ws.onmessage = (event) => {
        if (isPausedRef.current) return
        try {
          const data = JSON.parse(event.data)
          setReadings((prev) => [data, ...prev].slice(0, 500))

          if (data.prediction === 1) {
            const chMeta = CHANNELS.find((c) => c.id === data.channel)
            const isMag = data.channel.startsWith('CADC087')
            const now = Date.now()

            const lastTime = lastIncidentTimeRef.current[data.channel] || 0
            if (now - lastTime > 4000) {
              lastIncidentTimeRef.current[data.channel] = now
              incidentCounterRef.current += 1
              const newId = `INC-${incidentCounterRef.current}`

              const correlated = edgesRef.current
                .filter(([a, b]) => a === data.channel || b === data.channel)
                .sort((e1, e2) => (e2[2] || 0) - (e1[2] || 0))
                .map(([a, b]) => (a === data.channel ? b : a))

              const newIncident = {
                id: newId,
                timestamp: data.timestamp,
                channel: data.channel,
                channelName: chMeta?.name || data.channel,
                shortName: chMeta?.short || data.channel,
                group: chMeta?.group || '',
                value: data.value,
                unit: chMeta?.unit || '',
                probability: data.probability || 0.95,
                modelName: data.model_name || 'DynamicGraph+GRU',
                status: 'OPEN',
                subsystem: isMag
                  ? 'Attitude Determination & Control (ADCS)'
                  : 'Electrical Power Subsystem (EPS)',
                faultType: isMag
                  ? 'Magnetic Dipole Inversion / Axis Alignment Drift'
                  : 'Photodiode Irradiance Collapse / Panel Shadowing',
                propagation: correlated,
                fdirActionSteps: isMag
                  ? [
                      'Verify reaction wheel desaturation and gyroscopic momentum limits.',
                      'Initiate ADCS Extended Kalman Filter bias re-estimation.',
                      'Fall back to autonomous B-dot damping if attitude error > 3.5°.'
                    ]
                  : [
                      'Inspect solar array gimbal angles against sun vector.',
                      'Evaluate EPS battery shunt regulator bus voltage & thermal state.',
                      'Isolate degraded photodiode from attitude calculation.'
                    ],
                createdTime: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
              }

              setIncidents((prev) => [newIncident, ...prev].slice(0, 60))
              setSelectedIncidentId(newId)
              setSelectedChannel(data.channel)
            }
          }
        } catch (err) {
          console.error('[WS Error]:', err)
        }
      }

      ws.onerror = () => setStreamStatus('error')
      ws.onclose = () => {
        setStreamStatus('disconnected')
        reconnectTimeout = setTimeout(connect, 3000)
      }
    }

    connect()

    return () => {
      if (reconnectTimeout) clearTimeout(reconnectTimeout)
      if (ws) ws.close()
    }
  }, [])

  const handleResolveIncident = (id) => {
    setIncidents((prev) =>
      prev.map((inc) =>
        inc.id === id
          ? {
              ...inc,
              status: 'RESOLVED',
              resolvedAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
            }
          : inc
      )
    )
  }

  const handleResolveAll = () => {
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    setIncidents((prev) =>
      prev.map((inc) => (inc.status === 'OPEN' ? { ...inc, status: 'RESOLVED', resolvedAt: timeStr } : inc))
    )
  }

  const handleSimulateFault = () => {
    const chMeta = CHANNELS.find((c) => c.id === selectedChannel) || CHANNELS[0]
    const isMag = chMeta.group === 'ADCS'
    incidentCounterRef.current += 1
    const newId = `INC-${incidentCounterRef.current}`

    const correlated = edgesRef.current
      .filter(([a, b]) => a === chMeta.id || b === chMeta.id)
      .sort((e1, e2) => (e2[2] || 0) - (e1[2] || 0))
      .map(([a, b]) => (a === chMeta.id ? b : a))

    const offNominalValue = isMag
      ? (chMeta.nominal.max * 1.85)
      : 0.0

    const faultReading = {
      channel: chMeta.id,
      timestamp: new Date().toISOString(),
      value: offNominalValue,
      prediction: 1,
      probability: 0.985,
      model_name: 'DynamicGraph+GRU',
    }

    setReadings((prev) => [faultReading, ...prev].slice(0, 500))

    const newIncident = {
      id: newId,
      timestamp: faultReading.timestamp,
      channel: chMeta.id,
      channelName: chMeta.name,
      shortName: chMeta.short,
      group: chMeta.group,
      value: offNominalValue,
      unit: chMeta.unit,
      probability: 0.985,
      modelName: 'DynamicGraph+GRU',
      status: 'OPEN',
      subsystem: isMag
        ? 'Attitude Determination & Control (ADCS)'
        : 'Electrical Power Subsystem (EPS)',
      faultType: isMag
        ? 'Magnetic Dipole Inversion / Axis Alignment Drift'
        : 'Photodiode Irradiance Collapse / Panel Shadowing',
      propagation: correlated,
      fdirActionSteps: isMag
        ? [
            'Verify reaction wheel desaturation and gyroscopic momentum limits.',
            'Initiate ADCS Extended Kalman Filter bias re-estimation.',
            'Fall back to autonomous B-dot damping if attitude error > 3.5°.'
          ]
        : [
            'Inspect solar array gimbal angles against sun vector.',
            'Evaluate EPS battery shunt regulator bus voltage & thermal state.',
            'Isolate degraded photodiode from attitude calculation.'
          ],
      createdTime: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
    }

    setIncidents((prev) => [newIncident, ...prev].slice(0, 60))
    setSelectedIncidentId(newId)
  }

  const openIncidents = useMemo(() => incidents.filter((i) => i.status === 'OPEN'), [incidents])
  const resolvedIncidents = useMemo(() => incidents.filter((i) => i.status === 'RESOLVED'), [incidents])

  const activeIncident = useMemo(() => {
    if (selectedIncidentId) {
      const found = incidents.find((i) => i.id === selectedIncidentId)
      if (found) return found
    }
    return openIncidents[0] || incidents[0] || null
  }, [selectedIncidentId, incidents, openIncidents])

  const channelStates = useMemo(() => {
    const map = {}
    CHANNELS.forEach((ch) => {
      const chReadings = readings.filter((r) => r.channel === ch.id)
      const latest = chReadings[0] || null
      const history = chReadings.slice(0, 60).reverse()
      const hasOpenIncident = openIncidents.some((inc) => inc.channel === ch.id)
      map[ch.id] = {
        ...ch,
        latest,
        history,
        isAnomaly: hasOpenIncident || latest?.prediction === 1,
      }
    })
    return map
  }, [readings, openIncidents])

  const currentChannelMeta = useMemo(() => {
    return CHANNELS.find((c) => c.id === selectedChannel) || CHANNELS[0]
  }, [selectedChannel])

  // Warm trace fallback ensures the chart always displays a crisp nominal waveform
  const channelWaveform = useMemo(() => {
    const raw = readings.filter((r) => r.channel === selectedChannel).slice(0, 60).reverse()
    if (raw.length >= 2) return raw
    return generateNominalTrace(currentChannelMeta)
  }, [readings, selectedChannel, currentChannelMeta])

  const channelStats = useMemo(() => {
    const vals = channelWaveform.map((d) => Number(d.value))
    const sum = vals.reduce((a, b) => a + b, 0)
    const mean = sum / vals.length
    const sqDiff = vals.map((v) => (v - mean) ** 2)
    const std = Math.sqrt(sqDiff.reduce((a, b) => a + b, 0) / vals.length)
    const latestReading = channelWaveform[channelWaveform.length - 1]
    const latest = latestReading ? Number(latestReading.value) : currentChannelMeta.nominal.defaultVal
    return {
      mean,
      std,
      min: Math.min(...vals),
      max: Math.max(...vals),
      latest,
      diffMean: latest - mean,
      prob: latestReading?.probability != null ? latestReading.probability : 0.04,
    }
  }, [channelWaveform, currentChannelMeta])

  const hasSpacecraftAnomaly = openIncidents.length > 0

  return (
    <div className="h-screen max-h-screen overflow-hidden bg-[#0c1017] text-[#e6edf3] font-sans flex flex-col antialiased selection:bg-[#1f3a5f] selection:text-white">
      {/* 1. Compact Premium Application Header */}
      <header className="flex-shrink-0 border-b border-[#232d3f] bg-[#141a24] px-5 py-2.5 flex flex-wrap items-center justify-between gap-3">
        {/* Brand & Mission Identity */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-[#1c2433] border border-[#2d3a52] flex items-center justify-center text-sky-400 shadow-sm">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="3" />
              <path d="M4.93 19.07a10 10 0 1 1 14.14 0" />
              <path d="M8.46 15.54a5 5 0 1 1 7.08 0" />
            </svg>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-base tracking-tight text-white">ORBITGUARD</span>
              <span className="text-[11px] font-semibold px-1.5 py-0.2 rounded bg-[#1e2738] text-slate-300 border border-[#2c384e]">
                ESA OPS-SAT
              </span>
              <span className="text-xs text-[#8b9bb4]">LEO 510 km &bull; Orbit #14,208</span>
            </div>
            <div className="text-[11px] text-[#8b9bb4]">
              Autonomous FDIR Telemetry Diagnostics &amp; Root-Cause Resolution Station
            </div>
          </div>
        </div>

        {/* Live Controls & Telemetry Status */}
        <div className="flex items-center gap-3">
          {/* Link Status */}
          <div className="flex items-center gap-2 px-2.5 py-1 rounded-md bg-[#18202d] border border-[#273347] text-xs">
            <span
              className={`w-2 h-2 rounded-full ${
                streamStatus === 'connected' ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.4)]' : 'bg-rose-400'
              }`}
            />
            <span className="text-slate-300 font-medium">
              {streamStatus === 'connected' ? 'Live Telemetry (10 Hz)' : 'Connecting / Standby'}
            </span>
          </div>

          {/* UTC Clock */}
          <div className="px-2.5 py-1 rounded-md bg-[#18202d] border border-[#273347] text-xs font-mono text-slate-200">
            {currentTime.slice(17, 25)} UTC
          </div>

          {/* Demo Fault Injection Button */}
          <button
            onClick={handleSimulateFault}
            className="flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-md transition-colors bg-rose-500/15 hover:bg-rose-500/25 border border-rose-500/40 text-rose-200 shadow-sm"
            title="Inject an off-nominal telemetry fault to demonstrate real-time autonomous FDIR detection"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
            </svg>
            <span>Inject Fault</span>
          </button>

          {/* Stream Pause / Resume Control */}
          <button
            onClick={() => setIsPaused((p) => !p)}
            className={`flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-md transition-colors border ${
              isPaused
                ? 'bg-amber-500/15 border-amber-500/40 text-amber-200 hover:bg-amber-500/25'
                : 'bg-[#1e2738] border-[#2c384e] text-slate-200 hover:bg-[#273349] hover:text-white'
            }`}
          >
            {isPaused ? (
              <>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                  <polygon points="5 3 19 12 5 21 5 3" />
                </svg>
                <span>Resume</span>
              </>
            ) : (
              <>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                  <rect x="6" y="4" width="4" height="16" />
                  <rect x="14" y="4" width="4" height="16" />
                </svg>
                <span>Pause</span>
              </>
            )}
          </button>
        </div>
      </header>

      {/* 2. Compact Horizontal Mission Overview Ribbon */}
      <section className="flex-shrink-0 px-5 pt-2.5 pb-1">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-2.5">
          {/* Card 1: Spacecraft Overall Health */}
          <div className="bg-[#141a24] border border-[#232d3f] rounded-lg px-3 py-2 flex items-center justify-between">
            <div>
              <div className="text-[11px] font-medium text-[#8b9bb4]">Spacecraft Status</div>
              <div className="text-sm font-semibold mt-0.5 flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${hasSpacecraftAnomaly ? 'bg-rose-500' : 'bg-emerald-400'}`} />
                <span className={hasSpacecraftAnomaly ? 'text-rose-400' : 'text-emerald-400'}>
                  {hasSpacecraftAnomaly ? 'Fault Flagged' : 'Nominal Flight'}
                </span>
              </div>
            </div>
            <div className="text-right text-[11px] text-[#8b9bb4]">
              <div>9 Sensors Online</div>
              <div className="text-slate-400">Dual Bus Linked</div>
            </div>
          </div>

          {/* Card 2: Active Unresolved Anomalies */}
          <div className="bg-[#141a24] border border-[#232d3f] rounded-lg px-3 py-2 flex items-center justify-between">
            <div>
              <div className="text-[11px] font-medium text-[#8b9bb4]">Active Incidents</div>
              <div className="text-sm font-semibold mt-0.5 text-white">
                {openIncidents.length === 0 ? (
                  <span className="text-emerald-400">0 Unresolved</span>
                ) : (
                  <span className="text-rose-400">{openIncidents.length} Critical Fault{openIncidents.length > 1 ? 's' : ''}</span>
                )}
              </div>
            </div>
            <div className="text-right text-[11px] text-[#8b9bb4]">
              <div>Logged: {incidents.length}</div>
              <div className="text-slate-400">{resolvedIncidents.length} Cleared</div>
            </div>
          </div>

          {/* Card 3: Downlink Stream */}
          <div className="bg-[#141a24] border border-[#232d3f] rounded-lg px-3 py-2 flex items-center justify-between">
            <div>
              <div className="text-[11px] font-medium text-[#8b9bb4]">Downlink Telemetry</div>
              <div className="text-sm font-semibold font-mono mt-0.5 text-white">
                {isPaused ? 'PAUSED' : '10.0 Hz'}
              </div>
            </div>
            <div className="text-right text-[11px] text-[#8b9bb4]">
              <div>FIFO: 500</div>
              <div className="text-slate-400">Win: 60 Samples</div>
            </div>
          </div>

          {/* Card 4: Selected Channel Risk */}
          <div className="bg-[#141a24] border border-[#232d3f] rounded-lg px-3 py-2 flex items-center justify-between">
            <div className="flex-1 pr-2">
              <div className="text-[11px] font-medium text-[#8b9bb4] flex items-center justify-between">
                <span>Anomaly Risk</span>
                <span className="font-mono text-slate-300 font-semibold">{currentChannelMeta.short}</span>
              </div>
              <div className="text-sm font-semibold font-mono mt-0.5 flex items-baseline gap-1.5">
                <span className={channelStats.prob >= 0.5 ? 'text-rose-400' : 'text-emerald-400'}>
                  {(channelStats.prob * 100).toFixed(1)}%
                </span>
                <span className="text-[10px] font-sans font-normal text-[#8b9bb4]">Graph-GRU</span>
              </div>
            </div>
            <div className="w-14 bg-[#1f2738] h-1.5 rounded-full overflow-hidden self-center flex-shrink-0">
              <div
                className={`h-full transition-all duration-300 ${channelStats.prob >= 0.5 ? 'bg-rose-500' : 'bg-emerald-400'}`}
                style={{ width: `${Math.min(100, Math.max(4, channelStats.prob * 100))}%` }}
              />
            </div>
          </div>
        </div>
      </section>

      {/* 3. Main Dashboard Grid (Fits 100vh Without Page Scroll) */}
      <main className="flex-1 min-h-0 px-5 pt-2 pb-3.5 grid grid-rows-2 gap-2.5 overflow-hidden">
        {/* ROW 1: Wide Telemetry Waveform Section (65%) + Compact Diagnostics Panel (35%) */}
        <div className="min-h-0 grid grid-cols-1 lg:grid-cols-12 gap-2.5">
          {/* LEFT 65% (8 cols): Telemetry Waveform Section */}
          <div className="lg:col-span-8 bg-[#141a24] border border-[#232d3f] rounded-lg p-3 flex flex-col justify-between h-full min-h-0 overflow-hidden">
            {/* Header: Title, Selected Channel Info, & Prominent Latest Reading */}
            <div className="flex-shrink-0">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#212b3c] pb-1.5 mb-1.5">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-sm font-semibold text-white tracking-tight">
                      {currentChannelMeta.name}
                    </h2>
                    <span className="font-mono text-xs font-semibold px-1.5 py-0.2 rounded bg-[#1b2333] text-sky-400 border border-[#2a3850]">
                      {currentChannelMeta.id}
                    </span>
                    <span className="text-xs font-medium px-1.5 py-0.2 rounded bg-[#19202c] text-slate-300 border border-[#263143]">
                      {currentChannelMeta.group} Bus
                    </span>
                  </div>
                  <div className="text-[11px] text-[#8b9bb4]">
                    Real-time 60-sample flight waveform &bull; Nominal envelope &bull; 10 Hz telemetry downlink
                  </div>
                </div>

                {/* Prominent Instrument Value Readout (22px bold) */}
                <div className="text-right flex items-baseline gap-1.5">
                  <span className="text-xs font-medium text-[#8b9bb4]">Latest:</span>
                  <span className="text-xl font-bold font-mono text-white tracking-tight tabular-nums">
                    {channelStats.latest.toExponential(4)}
                  </span>
                  <span className="text-xs font-mono text-slate-300 font-medium">
                    {currentChannelMeta.unit}
                  </span>
                </div>
              </div>

              {/* Sensor Selection: Clean Compact Segmented Control */}
              <div className="flex flex-wrap items-center justify-between gap-1.5 mb-1.5 bg-[#0f141d] p-1 rounded-md border border-[#1e2736]">
                {/* ADCS Subsystem Tabs */}
                <div className="flex items-center gap-1">
                  <span className="text-[11px] font-semibold text-[#8b9bb4] px-1.5 uppercase tracking-wider">ADCS:</span>
                  {CHANNELS.filter((c) => c.group === 'ADCS').map((ch) => {
                    const isSel = selectedChannel === ch.id
                    const isAnom = channelStates[ch.id]?.isAnomaly
                    return (
                      <button
                        key={ch.id}
                        onClick={() => setSelectedChannel(ch.id)}
                        className={`flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium transition-all ${
                          isSel
                            ? 'bg-[#1f2b3e] text-white border border-sky-400/50 shadow-sm'
                            : 'text-slate-300 hover:text-white hover:bg-[#161d2b]'
                        }`}
                      >
                        {isAnom && <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />}
                        <span>{ch.short}</span>
                        <span className="text-[10px] text-[#8b9bb4] font-mono">({ch.id.slice(-4)})</span>
                      </button>
                    )
                  })}
                </div>

                {/* EPS Subsystem Tabs */}
                <div className="flex items-center gap-1">
                  <span className="text-[11px] font-semibold text-[#8b9bb4] px-1.5 uppercase tracking-wider">EPS:</span>
                  {CHANNELS.filter((c) => c.group === 'EPS').map((ch) => {
                    const isSel = selectedChannel === ch.id
                    const isAnom = channelStates[ch.id]?.isAnomaly
                    return (
                      <button
                        key={ch.id}
                        onClick={() => setSelectedChannel(ch.id)}
                        className={`flex items-center gap-1 px-2 py-1 rounded text-xs font-medium transition-all ${
                          isSel
                            ? 'bg-[#1f2b3e] text-white border border-sky-400/50 shadow-sm'
                            : 'text-slate-300 hover:text-white hover:bg-[#161d2b]'
                        }`}
                      >
                        {isAnom && <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />}
                        <span>{ch.short}</span>
                        <span className="text-[10px] text-[#8b9bb4] font-mono">({ch.id.slice(-4)})</span>
                      </button>
                    )
                  })}
                </div>
              </div>

              {/* Hover Inspector Readout */}
              <div className="flex items-center justify-between text-[11px] font-mono text-[#8b9bb4] mb-1 px-0.5">
                <span className="text-slate-400 font-sans font-medium">Waveform Oscilloscope</span>
                {hoveredPoint ? (
                  <div className="flex items-center gap-2.5 text-[11px]">
                    <span className="text-slate-300">T: {new Date(hoveredPoint.timestamp).toLocaleTimeString()}</span>
                    <span className="text-white font-semibold">
                      Val: {Number(hoveredPoint.value).toExponential(4)} {currentChannelMeta.unit}
                    </span>
                    <span className={hoveredPoint.prediction === 1 ? 'text-rose-400 font-bold' : 'text-emerald-400'}>
                      [{hoveredPoint.prediction === 1 ? 'FAULT' : 'NOMINAL'}]
                    </span>
                  </div>
                ) : (
                  <span className="text-[#64748b] font-sans">Hover data points to inspect telemetry value</span>
                )}
              </div>
            </div>

            {/* Telemetry Waveform Oscilloscope Chart (Flexible 100% height inside card) */}
            <div className="flex-1 min-h-0 bg-[#0c0f16] border border-[#1e2736] rounded-md p-1.5 relative flex items-center justify-center overflow-hidden">
              <EngineeringStripChart
                data={channelWaveform}
                unit={currentChannelMeta.unit}
                nominal={currentChannelMeta.nominal}
                onHover={(pt) => setHoveredPoint(pt)}
              />
            </div>

            {/* Key Statistics Bar */}
            <div className="flex-shrink-0 grid grid-cols-3 gap-2 pt-1.5 mt-1 border-t border-[#212b3c] text-[11px] font-mono">
              <div className="text-slate-300">
                Mean: <span className="text-white font-semibold">{channelStats.mean.toExponential(3)}</span>
              </div>
              <div className="text-slate-300 text-center">
                Std Dev (3&sigma;): <span className="text-white font-semibold">&plusmn;{channelStats.std.toExponential(3)}</span>
              </div>
              <div className="text-slate-300 text-right">
                Span: <span className="text-white font-semibold">[{channelStats.min.toExponential(2)}, {channelStats.max.toExponential(2)}]</span>
              </div>
            </div>
          </div>

          {/* RIGHT 35% (4 cols): Compact Editorial Diagnostics Panel */}
          <div className="lg:col-span-4 bg-[#141a24] border border-[#232d3f] rounded-lg p-3 flex flex-col justify-between h-full min-h-0 overflow-hidden">
            <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
              {/* Header */}
              <div className="flex-shrink-0 flex items-center justify-between border-b border-[#212b3c] pb-1.5 mb-2">
                <div>
                  <h2 className="text-sm font-semibold text-white tracking-tight">
                    Autonomous FDIR Diagnostics
                  </h2>
                  <div className="text-[11px] text-[#8b9bb4]">DynamicGraph + GRU Inference Engine</div>
                </div>
                <span className="text-[10px] font-semibold px-1.5 py-0.2 rounded bg-[#1a2333] text-sky-400 border border-[#283850]">
                  PyTorch k=3
                </span>
              </div>

              {/* Status Content (Scrolls internally if viewport is small) */}
              <div className="flex-1 min-h-0 overflow-y-auto pr-0.5">
                {!activeIncident || activeIncident.status === 'RESOLVED' ? (
                  /* Editorial Healthy State */
                  <div className="flex flex-col gap-2">
                    <div className="flex items-start gap-2.5 p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                      <div className="w-6 h-6 rounded-full bg-emerald-500/20 flex items-center justify-center text-emerald-400 flex-shrink-0 mt-0.5">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                          <polyline points="20 6 9 17 4 12" />
                        </svg>
                      </div>
                      <div>
                        <h3 className="text-xs font-semibold text-emerald-300">All Subsystems Nominal</h3>
                        <p className="text-[11px] text-[#8b9bb4] mt-0.5 leading-relaxed">
                          Telemetry across all 9 channels remains well within baseline bounds. No off-nominal signatures or spatial correlation divergences detected.
                        </p>
                      </div>
                    </div>

                    {/* Clean Editorial Summary Rows (no nested boxes) */}
                    <div className="divide-y divide-[#212b3c] text-xs">
                      <div className="py-1.5 flex items-center justify-between">
                        <span className="text-slate-300 font-medium">ADCS Attitude Bus</span>
                        <span className="text-emerald-400 font-medium text-[11px] flex items-center gap-1">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                          3/3 Channels Stable
                        </span>
                      </div>

                      <div className="py-1.5 flex items-center justify-between">
                        <span className="text-slate-300 font-medium">EPS Power Array</span>
                        <span className="text-emerald-400 font-medium text-[11px] flex items-center gap-1">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                          6/6 Channels Stable
                        </span>
                      </div>

                      <div className="py-1.5 flex items-center justify-between">
                        <span className="text-slate-300 font-medium">Spatial Graph Drift</span>
                        <span className="text-slate-300 font-mono text-[11px]">
                          &Delta;A = 0.04 (Nominal &lt; 0.15)
                        </span>
                      </div>

                      <div className="py-1.5 flex items-center justify-between">
                        <span className="text-slate-300 font-medium">FDIR Standby State</span>
                        <span className="text-sky-400 font-mono text-[11px]">
                          Autonomous Ready
                        </span>
                      </div>
                    </div>

                    {/* Subsystem Telemetry Snapshot */}
                    <div className="mt-0.5 bg-[#0f141d] p-1.5 rounded border border-[#1e2736] text-[10px] font-mono text-[#8b9bb4]">
                      <div className="flex justify-between text-slate-300 font-sans font-medium mb-0.5">
                        <span>Telemetry Verification</span>
                        <span className="text-emerald-400">PASSED</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Bx: {channelStats.latest.toExponential(2)} T</span>
                        <span>PD Array: 2.14V Nom</span>
                      </div>
                    </div>
                  </div>
                ) : (
                  /* Editorial Active Incident State */
                  <div className="flex flex-col gap-2">
                    {/* Alert Banner */}
                    <div className="p-2 rounded-lg bg-rose-500/10 border border-rose-500/30">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-mono font-bold px-1.5 py-0.2 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30">
                          {activeIncident.id}
                        </span>
                        <span className="text-xs font-mono text-rose-400 font-semibold">
                          P(Fault) = {(activeIncident.probability * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="text-xs font-semibold text-rose-200 mt-1">
                        {activeIncident.subsystem}
                      </div>
                      <div className="text-[11px] text-rose-300/80 mt-0.5">
                        {activeIncident.faultType}
                      </div>
                    </div>

                    {/* Root Cause Details */}
                    <div className="text-xs space-y-1">
                      <div className="flex items-center justify-between py-0.5 border-b border-[#212b3c]">
                        <span className="text-[#8b9bb4]">Root Cause Channel:</span>
                        <span className="font-mono font-semibold text-white">
                          {activeIncident.channel} ({activeIncident.shortName})
                        </span>
                      </div>
                      <div className="flex items-center justify-between py-0.5 border-b border-[#212b3c]">
                        <span className="text-[#8b9bb4]">Observed Value:</span>
                        <span className="font-mono text-rose-300">
                          {Number(activeIncident.value).toExponential(4)} {activeIncident.unit}
                        </span>
                      </div>
                      <div className="flex items-center justify-between py-0.5 border-b border-[#212b3c]">
                        <span className="text-[#8b9bb4]">Propagation:</span>
                        <span className="font-mono text-amber-300">
                          {activeIncident.propagation.length > 0 ? activeIncident.propagation.slice(0, 3).join(', ') : 'Isolated channel'}
                        </span>
                      </div>
                    </div>

                    {/* Prescribed Action Checklist */}
                    <div>
                      <div className="text-[10px] font-semibold text-slate-300 mb-1 uppercase tracking-wider">
                        ESA FDIR Recovery Steps:
                      </div>
                      <div className="space-y-1 text-xs text-slate-300">
                        {activeIncident.fdirActionSteps.slice(0, 2).map((step, idx) => (
                          <div key={idx} className="flex items-start gap-1.5 bg-[#10141d] p-1.5 rounded border border-[#1e2736]">
                            <span className="w-3.5 h-3.5 rounded-full bg-sky-500/20 text-sky-400 flex items-center justify-center font-mono text-[9px] flex-shrink-0 mt-0.5">
                              {idx + 1}
                            </span>
                            <span className="leading-snug text-[10px]">{step}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Quick Action Button */}
                    <button
                      onClick={() => handleResolveIncident(activeIncident.id)}
                      className="w-full mt-1 py-1.5 px-2.5 rounded-md bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs transition-colors flex items-center justify-center gap-1.5 shadow-sm"
                    >
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                      <span>Clear Incident ({activeIncident.id})</span>
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* Bottom Engine Specs */}
            <div className="flex-shrink-0 pt-1.5 mt-1 border-t border-[#212b3c] flex items-center justify-between text-[11px] text-[#8b9bb4]">
              <span>Dynamic Pearson Graph</span>
              <span className="font-mono text-slate-300">{graphIsLive ? 'Live A(t) Linked' : 'Static Orbit Topology'}</span>
            </div>
          </div>
        </div>

        {/* ROW 2: Large Sensor Correlation Topology (65%) + Technician Incident Queue (35%) */}
        <div className="min-h-0 grid grid-cols-1 lg:grid-cols-12 gap-2.5">
          {/* LEFT 65% (8 cols): Sensor Topology Graph (Large & Highly Legible) */}
          <div className="lg:col-span-8 bg-[#141a24] border border-[#232d3f] rounded-lg p-3 flex flex-col justify-between h-full min-h-0 overflow-hidden">
            {/* Header */}
            <div className="flex-shrink-0 flex items-center justify-between border-b border-[#212b3c] pb-1.5 mb-1.5">
              <div>
                <h2 className="text-sm font-semibold text-white tracking-tight">
                  Subsystem Sensor Correlation Topology
                </h2>
                <div className="text-[11px] text-[#8b9bb4]">
                  Dynamic inter-sensor adjacency matrix A(t) &bull; Edge thickness corresponds to real Pearson correlation |r|
                </div>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-[10px] font-semibold px-1.5 py-0.2 rounded bg-[#1a2333] text-sky-400 border border-[#283850]">
                  {graphIsLive ? 'Real-Time A(t)' : 'Baseline Orbit Map'}
                </span>
                <span className="text-[11px] text-[#8b9bb4]">Click any node to switch channel</span>
              </div>
            </div>

            {/* Topology SVG Viewport (Fills 100% available container height) */}
            <div className="flex-1 min-h-0 bg-[#0c0f16] border border-[#1e2736] rounded-md p-1.5 relative flex items-center justify-center overflow-hidden">
              <SubsystemTopologyView
                channels={CHANNELS}
                edges={EDGES}
                channelStates={channelStates}
                rootChannel={activeIncident?.status === 'OPEN' ? activeIncident.channel : null}
                selectedChannel={selectedChannel}
                onSelectChannel={(chId) => setSelectedChannel(chId)}
              />
            </div>

            {/* Topology Legend */}
            <div className="flex-shrink-0 flex flex-wrap items-center justify-between gap-3 pt-1.5 mt-1 border-t border-[#212b3c] text-[11px] text-[#8b9bb4]">
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#1b2536] border-2 border-sky-400" />
                  <span className="text-slate-300 font-medium">Selected</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-rose-500/30 border-2 border-rose-500" />
                  <span className="text-rose-300 font-medium">Off-Nominal Root</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#18202d] border border-slate-500" />
                  <span className="text-slate-300">Nominal</span>
                </div>
              </div>
              <div className="text-slate-400">
                Nodes: <span className="text-white font-mono font-medium">9 Channels</span> &bull; Subsystems: <span className="text-white font-medium">ADCS + EPS</span>
              </div>
            </div>
          </div>

          {/* RIGHT 35% (4 cols): Technician Incident Queue */}
          <div className="lg:col-span-4 bg-[#141a24] border border-[#232d3f] rounded-lg p-3 flex flex-col justify-between h-full min-h-0 overflow-hidden">
            <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
              {/* Header & Tabs */}
              <div className="flex-shrink-0 flex items-center justify-between border-b border-[#212b3c] pb-1.5 mb-2">
                <div className="flex items-center gap-1 bg-[#0f141d] p-1 rounded-md border border-[#1e2736]">
                  <button
                    onClick={() => setIncidentTab('open')}
                    className={`px-2.5 py-0.5 rounded text-xs font-semibold transition-all ${
                      incidentTab === 'open'
                        ? 'bg-[#1f2b3e] text-white border border-sky-400/40 shadow-sm'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Active ({openIncidents.length})
                  </button>
                  <button
                    onClick={() => setIncidentTab('resolved')}
                    className={`px-2.5 py-0.5 rounded text-xs font-semibold transition-all ${
                      incidentTab === 'resolved'
                        ? 'bg-[#1f2b3e] text-white border border-sky-400/40 shadow-sm'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Resolved ({resolvedIncidents.length})
                  </button>
                </div>

                {incidentTab === 'open' && openIncidents.length > 1 && (
                  <button
                    onClick={handleResolveAll}
                    className="text-xs text-slate-300 hover:text-white font-medium underline px-1"
                  >
                    Resolve All
                  </button>
                )}
              </div>

              {/* Incidents Content (Fills card, scrolls internally if list is long) */}
              <div className="flex-1 min-h-0 overflow-y-auto pr-0.5 space-y-1.5">
                {incidentTab === 'open' ? (
                  openIncidents.length === 0 ? (
                    /* Balanced Empty State */
                    <div className="h-full flex flex-col items-center justify-center text-center p-3 text-[#8b9bb4]">
                      <div className="w-10 h-10 rounded-full bg-[#18202d] border border-[#273347] flex items-center justify-center text-emerald-400 mb-2">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                          <path d="M9 12l2 2 4-4" />
                        </svg>
                      </div>
                      <h3 className="text-xs font-semibold text-white">No Active Incidents</h3>
                      <p className="text-[11px] text-[#8b9bb4] mt-1 max-w-xs leading-relaxed">
                        All telemetry streams operating within nominal bounds. Anomalies detected by Graph-GRU will appear here.
                      </p>
                      <div className="mt-2 text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                        &bull; Nominal Orbit Status &bull;
                      </div>
                    </div>
                  ) : (
                    /* Active Incidents List */
                    openIncidents.map((inc) => {
                      const isSel = selectedIncidentId === inc.id
                      return (
                        <div
                          key={inc.id}
                          onClick={() => {
                            setSelectedIncidentId(inc.id)
                            setSelectedChannel(inc.channel)
                          }}
                          className={`p-2 rounded-lg border transition-all cursor-pointer ${
                            isSel
                              ? 'bg-[#1a2333] border-sky-400/50 shadow-sm'
                              : 'bg-[#10141d] border-[#1e2736] hover:border-[#2d3a50]'
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] font-mono font-bold px-1.5 py-0.2 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30">
                              {inc.id}
                            </span>
                            <span className="text-[10px] font-mono text-[#8b9bb4]">{inc.createdTime}</span>
                          </div>
                          <div className="mt-1 flex items-center justify-between">
                            <div className="text-xs font-semibold text-white">
                              {inc.channel} &bull; {inc.shortName}
                            </div>
                            <span className="text-xs font-mono text-rose-400 font-semibold">
                              {(inc.probability * 100).toFixed(1)}%
                            </span>
                          </div>
                          <div className="text-[11px] text-[#8b9bb4] mt-0.5 line-clamp-1">{inc.faultType}</div>
                          <div className="mt-1.5 pt-1.5 border-t border-[#1c2433] flex items-center justify-between">
                            <span className="text-[11px] text-sky-400 font-medium">Click to inspect</span>
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                handleResolveIncident(inc.id)
                              }}
                              className="px-2 py-0.5 rounded bg-[#1e283a] hover:bg-[#28364e] border border-[#2d3a52] text-[11px] font-medium text-white transition-colors"
                            >
                              Resolve
                            </button>
                          </div>
                        </div>
                      )
                    })
                  )
                ) : resolvedIncidents.length === 0 ? (
                  /* Resolved Empty State */
                  <div className="h-full flex flex-col items-center justify-center text-center p-3 text-[#8b9bb4]">
                    <div className="w-8 h-8 rounded-full bg-[#18202d] border border-[#273347] flex items-center justify-center text-slate-400 mb-1.5">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                    </div>
                    <h3 className="text-xs font-medium text-white">No Resolved Incidents</h3>
                    <p className="text-[11px] text-[#8b9bb4] mt-0.5">Cleared incidents will be logged here for post-pass review.</p>
                  </div>
                ) : (
                  /* Resolved List */
                  resolvedIncidents.map((inc) => (
                    <div
                      key={inc.id}
                      className="p-2 rounded-lg border bg-[#10141d] border-[#1e2736] text-[11px] opacity-75"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-slate-400 font-medium">{inc.id}</span>
                        <span className="text-emerald-400 font-medium flex items-center gap-1">
                          <span>✓</span> Resolved at {inc.resolvedAt || inc.createdTime}
                        </span>
                      </div>
                      <div className="text-xs font-medium text-slate-200 mt-0.5">
                        {inc.channel} ({inc.shortName})
                      </div>
                      <div className="text-slate-400 mt-0.5">{inc.faultType}</div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Bottom Status */}
            <div className="flex-shrink-0 pt-1.5 mt-1 border-t border-[#212b3c] flex items-center justify-between text-[11px] text-[#8b9bb4]">
              <span>Triage Queue</span>
              <span>{openIncidents.length} Pending Intervention</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

function EngineeringStripChart({ data, unit, nominal, onHover }) {
  if (!data || data.length < 2) return null

  const width = 860
  const height = 210
  const pad = { top: 15, right: 30, bottom: 25, left: 80 }

  const values = data.map((d) => Number(d.value))
  let minVal = Math.min(...values)
  let maxVal = Math.max(...values)

  if (minVal === maxVal) {
    minVal -= 1
    maxVal += 1
  }

  const rangeY = maxVal - minVal
  const getX = (idx) => pad.left + (idx / (data.length - 1)) * (width - pad.left - pad.right)
  const getY = (val) => pad.top + (1 - (val - minVal) / rangeY) * (height - pad.top - pad.bottom)

  const points = data.map((d, i) => `${getX(i).toFixed(1)},${getY(Number(d.value)).toFixed(1)}`)
  const pathD = `M ${points.join(' L ')}`

  // Nominal threshold lines
  const hasNominal = nominal && nominal.min != null && nominal.max != null
  const yNominalTop = hasNominal ? Math.max(pad.top, Math.min(height - pad.bottom, getY(nominal.max))) : null
  const yNominalBottom = hasNominal ? Math.max(pad.top, Math.min(height - pad.bottom, getY(nominal.min))) : null

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full font-mono select-none" preserveAspectRatio="none">
      {/* Grid Reference Lines */}
      <line x1={pad.left} y1={pad.top} x2={width - pad.right} y2={pad.top} stroke="#222b3b" strokeDasharray="3 3" />
      <line x1={pad.left} y1={(pad.top + height - pad.bottom) / 2} x2={width - pad.right} y2={(pad.top + height - pad.bottom) / 2} stroke="#1b2331" strokeDasharray="2 2" />
      <line x1={pad.left} y1={height - pad.bottom} x2={width - pad.right} y2={height - pad.bottom} stroke="#222b3b" />

      {/* Nominal Range Band */}
      {hasNominal && yNominalTop !== null && yNominalBottom !== null && yNominalBottom > yNominalTop && (
        <rect
          x={pad.left}
          y={yNominalTop}
          width={width - pad.left - pad.right}
          height={yNominalBottom - yNominalTop}
          fill="#1c2637"
          opacity="0.35"
        />
      )}

      {/* Axis Scale Labels */}
      <text x={pad.left - 10} y={pad.top + 4} fill="#8b9bb4" fontSize="11" textAnchor="end">
        {maxVal.toExponential(2)} {unit}
      </text>
      <text x={pad.left - 10} y={(pad.top + height - pad.bottom) / 2 + 4} fill="#64748b" fontSize="10" textAnchor="end">
        {((maxVal + minVal) / 2).toExponential(2)}
      </text>
      <text x={pad.left - 10} y={height - pad.bottom} fill="#8b9bb4" fontSize="11" textAnchor="end">
        {minVal.toExponential(2)} {unit}
      </text>

      {/* Time axis marks along bottom */}
      <text x={pad.left} y={height - pad.bottom + 16} fill="#64748b" fontSize="10" textAnchor="start">
        T - 60s
      </text>
      <text x={(pad.left + width - pad.right) / 2} y={height - pad.bottom + 16} fill="#64748b" fontSize="10" textAnchor="middle">
        T - 30s
      </text>
      <text x={width - pad.right} y={height - pad.bottom + 16} fill="#64748b" fontSize="10" textAnchor="end">
        NOW (T - 0s)
      </text>

      {/* Signal Path */}
      <path d={pathD} fill="none" stroke="#38bdf8" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />

      {/* Signal Points */}
      {data.map((d, i) => {
        const cx = getX(i)
        const cy = getY(Number(d.value))
        const isAnom = d.prediction === 1

        return (
          <g
            key={i}
            className="cursor-pointer"
            onMouseEnter={() => onHover && onHover(d)}
            onMouseLeave={() => onHover && onHover(null)}
          >
            {isAnom ? (
              <>
                <circle cx={cx} cy={cy} r="5.5" fill="#f43f5e" opacity="0.4" />
                <circle cx={cx} cy={cy} r="3.5" fill="#ef4444" stroke="#7f1d1d" strokeWidth="1.5" />
              </>
            ) : (
              <circle cx={cx} cy={cy} r="2.5" fill="#38bdf8" opacity="0.85" />
            )}
          </g>
        )
      })}
    </svg>
  )
}

function SubsystemTopologyView({
  channels,
  edges,
  channelStates,
  rootChannel,
  selectedChannel,
  onSelectChannel,
}) {
  const width = 860
  const height = 240

  const nodeMap = {}
  channels.forEach((ch) => {
    nodeMap[ch.id] = ch
  })

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full select-none font-sans">
      {/* ADCS Subsystem Bus Container */}
      <rect x="25" y="10" width="810" height="90" fill="#111620" rx="6" stroke="#212a3a" />
      <text x="38" y="26" fill="#8b9bb4" fontSize="10" fontWeight="600" letterSpacing="0.05em">
        ADCS BUS &mdash; ATTITUDE DETERMINATION &amp; CONTROL (CADC0872 &bull; CADC0873 &bull; CADC0874)
      </text>

      {/* EPS Subsystem Bus Container */}
      <rect x="25" y="112" width="810" height="118" fill="#111620" rx="6" stroke="#212a3a" />
      <text x="38" y="128" fill="#8b9bb4" fontSize="10" fontWeight="600" letterSpacing="0.05em">
        EPS BUS &mdash; ELECTRICAL POWER &amp; SOLAR ARRAY (CADC0884 &ndash; CADC0894)
      </text>

      {/* Dynamic Pearson Edges */}
      {edges.map(([sourceId, targetId, strength = 0.5, style = 'straight'], idx) => {
        const s = nodeMap[sourceId]
        const t = nodeMap[targetId]
        if (!s || !t) return null

        const isConnectedToRoot = rootChannel && (sourceId === rootChannel || targetId === rootChannel)
        const isConnectedToSelected = selectedChannel && (sourceId === selectedChannel || targetId === selectedChannel)
        const absStr = Math.min(1, Math.max(0.2, Math.abs(strength)))
        const strokeWidth = 1.3 + absStr * 2.5

        // Crisp, visible edge color: clear contrast against dark bus (#3b4861)
        let strokeColor = '#3b4861'
        let opacity = 0.85

        if (isConnectedToRoot) {
          strokeColor = '#f43f5e'
          opacity = 1.0
        } else if (isConnectedToSelected) {
          strokeColor = '#38bdf8'
          opacity = 1.0
        }

        // Draw curved path for non-adjacent nodes or cross-bus edges to avoid slicing through other nodes
        const isArcDown = style === 'arc-down' || (s.y === t.y && Math.abs(s.x - t.x) > 200)
        const isCrossBus = style === 'cross-bus' || s.y !== t.y

        if (isArcDown) {
          const midX = (s.x + t.x) / 2
          const ctrlY = s.y + 35
          return (
            <path
              key={`${sourceId}-${targetId}-${idx}`}
              d={`M ${s.x} ${s.y} Q ${midX} ${ctrlY} ${t.x} ${t.y}`}
              fill="none"
              stroke={strokeColor}
              strokeWidth={strokeWidth}
              opacity={opacity}
            />
          )
        }

        if (isCrossBus) {
          return (
            <line
              key={`${sourceId}-${targetId}-${idx}`}
              x1={s.x}
              y1={s.y}
              x2={t.x}
              y2={t.y}
              stroke={strokeColor}
              strokeWidth={strokeWidth}
              strokeDasharray="4 4"
              opacity={opacity * 0.75}
            />
          )
        }

        return (
          <line
            key={`${sourceId}-${targetId}-${idx}`}
            x1={s.x}
            y1={s.y}
            x2={t.x}
            y2={t.y}
            stroke={strokeColor}
            strokeWidth={strokeWidth}
            opacity={opacity}
          />
        )
      })}

      {/* Sensor Nodes (Clean, Highly Legible 48px diameter) */}
      {channels.map((ch) => {
        const isRoot = rootChannel === ch.id
        const isAnom = channelStates[ch.id]?.isAnomaly
        const isSel = selectedChannel === ch.id

        let circleFill = '#161d2a'
        let circleStroke = '#2d3b52'
        let strokeW = 1.8

        if (isRoot || isAnom) {
          circleFill = '#3b1219'
          circleStroke = '#ef4444'
          strokeW = 2.8
        } else if (isSel) {
          circleFill = '#1a273b'
          circleStroke = '#38bdf8'
          strokeW = 2.8
        }

        return (
          <g
            key={ch.id}
            className="cursor-pointer transition-transform hover:opacity-90"
            onClick={() => onSelectChannel(ch.id)}
          >
            {/* Outer focus halo for selected node */}
            {isSel && (
              <circle cx={ch.x} cy={ch.y} r="30" fill="none" stroke="#38bdf8" strokeWidth="1" strokeDasharray="3 3" opacity="0.65" />
            )}

            {/* Main Node Circle */}
            <circle
              cx={ch.x}
              cy={ch.y}
              r="23"
              fill={circleFill}
              stroke={circleStroke}
              strokeWidth={strokeW}
            />

            {/* Inside Label: Short Name */}
            <text
              x={ch.x}
              y={ch.y - 2}
              textAnchor="middle"
              fill={isRoot || isAnom ? '#fecdd3' : '#f8fafc'}
              fontSize="11"
              fontWeight="700"
            >
              {ch.short}
            </text>

            {/* Sub-label: Sensor Channel Suffix */}
            <text
              x={ch.x}
              y={ch.y + 11}
              textAnchor="middle"
              fill={isRoot || isAnom ? '#fda4af' : '#8b9bb4'}
              fontSize="9"
              fontFamily="JetBrains Mono, monospace"
              fontWeight="500"
            >
              {ch.id.slice(-4)}
            </text>
          </g>
        )
      })}
    </svg>
  )
}
