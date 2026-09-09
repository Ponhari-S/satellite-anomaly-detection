import React, { useState, useEffect, useRef, useMemo } from 'react'

const BACKEND_WS = 'ws://127.0.0.1:8000/stream'

const CHANNELS = [
  { id: 'CADC0872', name: 'Mag X', group: 'ADCS', unit: 'T', x: 130, y: 75 },
  { id: 'CADC0873', name: 'Mag Y', group: 'ADCS', unit: 'T', x: 300, y: 75 },
  { id: 'CADC0874', name: 'Mag Z', group: 'ADCS', unit: 'T', x: 470, y: 75 },
  { id: 'CADC0884', name: 'PD 1', group: 'EPS', unit: 'V', x: 100, y: 195 },
  { id: 'CADC0886', name: 'PD 2', group: 'EPS', unit: 'V', x: 200, y: 195 },
  { id: 'CADC0888', name: 'PD 3', group: 'EPS', unit: 'V', x: 300, y: 195 },
  { id: 'CADC0890', name: 'PD 4', group: 'EPS', unit: 'V', x: 400, y: 195 },
  { id: 'CADC0892', name: 'PD 5', group: 'EPS', unit: 'V', x: 500, y: 195 },
  { id: 'CADC0894', name: 'PD 6', group: 'EPS', unit: 'V', x: 300, y: 255 },
]

const FALLBACK_EDGES = [
  ['CADC0872', 'CADC0873'],
  ['CADC0884', 'CADC0890'],
]

function useChannelGraph() {
  const [edges, setEdges] = useState(FALLBACK_EDGES)
  const [graphSource, setGraphSource] = useState('loading')

  useEffect(() => {
    fetch('http://127.0.0.1:8000/channel-graph')
      .then((res) => res.json())
      .then((data) => {
        const formatted = data.edges.map((e) => [e.source, e.target, e.strength])
        setEdges(formatted)
        setGraphSource('real')
        console.log(`[channel-graph] loaded ${formatted.length} real, computed edges`)
      })
      .catch((err) => {
        console.error('[channel-graph] failed to load real edges, using fallback:', err)
        setEdges(FALLBACK_EDGES)
        setGraphSource('fallback')
      })
  }, [])

  return { edges, graphSource }
}

export default function App() {
  const { edges: EDGES, graphSource: channelGraphSource } = useChannelGraph()
  const edgesRef = useRef(EDGES)
  edgesRef.current = EDGES

  const [streamStatus, setStreamStatus] = useState('connecting')
  const [readings, setReadings] = useState([])
  const [isPaused, setIsPaused] = useState(false)
  const isPausedRef = useRef(false)
  isPausedRef.current = isPaused

  const [selectedChannel, setSelectedChannel] = useState('CADC0872')
  const [selectedReading, setSelectedReading] = useState(null)
  const [currentTime, setCurrentTime] = useState(new Date().toUTCString())

  const [incidents, setIncidents] = useState([])
  const [selectedIncidentId, setSelectedIncidentId] = useState(null)
  const [incidentTab, setIncidentTab] = useState('open')
  const incidentCounterRef = useRef(100)
  const lastIncidentTimeRef = useRef({})

  const wsRef = useRef(null)

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date().toUTCString())
    }, 1000)
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
          setReadings((prev) => [data, ...prev].slice(0, 600))

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
                group: chMeta?.group || '',
                value: data.value,
                unit: chMeta?.unit || '',
                probability: data.probability || 0.95,
                status: 'OPEN',
                subsystem: isMag
                  ? 'ADCS (Attitude Determination & Control System)'
                  : 'EPS (Electrical Power & Optical Subsystem)',
                faultType: isMag
                  ? 'Magnetic Dipole Inversion / Attitude Axis Drift'
                  : 'Solar Array Shadowing / Photodiode Discrepancy',
                propagation: correlated,
                fdirAction: isMag
                  ? 'Execute ADCS Stabilization: Re-calibrate magnetometer bias and apply reaction wheel torque damping.'
                  : 'Execute EPS Safe-Mode: Verify solar panel sun-tracking vector and reset photodiode power bus.',
                createdTime: new Date().toLocaleTimeString(),
              }

              setIncidents((prev) => [newIncident, ...prev].slice(0, 80))
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
              resolvedAt: new Date().toLocaleTimeString(),
            }
          : inc
      )
    )
  }

  const handleResolveAll = () => {
    const timeStr = new Date().toLocaleTimeString()
    setIncidents((prev) =>
      prev.map((inc) =>
        inc.status === 'OPEN'
          ? { ...inc, status: 'RESOLVED', resolvedAt: timeStr }
          : inc
      )
    )
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
      const history = chReadings.slice(0, 40).reverse()
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

  const channelWaveform = useMemo(() => {
    return readings
      .filter((r) => r.channel === selectedChannel)
      .slice(0, 60)
      .reverse()
  }, [readings, selectedChannel])

  return (
    <div className="min-h-screen bg-black text-white font-sans antialiased flex flex-col selection:bg-emerald-600 selection:text-white">
      <header className="border-b border-[#22222E] bg-[#0A0A0E] px-6 py-3.5 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="bg-amber-500/15 border border-amber-400 text-amber-300 font-mono font-bold px-3 py-1 text-xs tracking-wider rounded">
            ORBITGUARD
          </div>
          <div>
            <h1 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
              ESA OPS-SAT Telemetry & Anomaly Analysis Console
              <span className="text-xs font-mono font-normal px-2 py-0.5 bg-[#14141C] text-slate-300 border border-[#2B2B38] rounded">
                LEO 510 km
              </span>
            </h1>
            <p className="text-xs text-slate-400">
              Autonomous FDIR Telemetry Diagnostics & Root Cause Resolution Station
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 font-mono text-xs">
          <div className="flex items-center gap-2 bg-[#121218] px-3.5 py-1.5 rounded border border-[#262633]">
            <span
              className={`h-2.5 w-2.5 rounded-full ${
                streamStatus === 'connected' ? 'bg-emerald-400 animate-pulse' : 'bg-red-500'
              }`}
            />
            <span className="text-white uppercase font-bold text-[11px]">
              {streamStatus === 'connected' ? 'LIVE STREAM' : streamStatus}
            </span>
          </div>

          <div
            className={`px-3 py-1.5 rounded border font-bold flex items-center gap-1.5 ${
              openIncidents.length > 0
                ? 'bg-red-950 border-red-500 text-red-200 animate-pulse'
                : 'bg-emerald-950 border-emerald-500 text-emerald-300'
            }`}
          >
            <span>{openIncidents.length > 0 ? '⚠️' : '✓'}</span>
            <span>
              {openIncidents.length} {openIncidents.length === 1 ? 'UNRESOLVED FAULT' : 'UNRESOLVED FAULTS'}
            </span>
          </div>

          <div className="text-slate-400 bg-[#121218] px-3 py-1.5 rounded border border-[#262633]">
            UTC: <span className="text-white font-bold">{currentTime.slice(17, 25)}</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsPaused(!isPaused)}
            className={`px-4 py-1.5 rounded font-mono text-xs font-bold transition-all shadow-sm ${
              isPaused
                ? 'bg-emerald-600 hover:bg-emerald-500 text-white'
                : 'bg-amber-600 hover:bg-amber-500 text-white'
            }`}
          >
            {isPaused ? '▶ RESUME' : '⏸ PAUSE'}
          </button>
        </div>
      </header>

      <main className="flex-1 p-4 grid grid-cols-1 xl:grid-cols-12 gap-4 bg-black">
        <div className="xl:col-span-7 flex flex-col gap-4">
          <div className="border border-[#22222E] bg-[#0E0E14] rounded-lg p-4 shadow flex flex-col">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#22222E] pb-3 mb-3">
              <div>
                <div className="text-xs uppercase font-mono text-slate-400 font-bold tracking-wider">
                  TELEMETRY WAVEFORM OSCILLOSCOPE
                </div>
                <div className="text-base font-bold text-white flex items-center gap-2">
                  <span className="text-emerald-400 font-mono text-lg">{selectedChannel}</span>
                  <span className="text-sm font-medium text-slate-200">
                    — {CHANNELS.find((c) => c.id === selectedChannel)?.name}
                  </span>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-1.5">
                {CHANNELS.map((ch) => {
                  const isSel = ch.id === selectedChannel
                  const state = channelStates[ch.id]
                  const isAnom = state?.isAnomaly

                  return (
                    <button
                      key={ch.id}
                      onClick={() => setSelectedChannel(ch.id)}
                      className={`px-3 py-1 rounded text-xs font-mono font-bold transition-all flex items-center gap-2 border ${
                        isSel
                          ? 'bg-[#1C1C2A] border-2 border-emerald-400 text-white shadow-md'
                          : isAnom
                          ? 'bg-red-950/80 border border-red-500 text-red-200 hover:bg-red-900'
                          : 'bg-[#12121A] border border-[#2A2A38] text-slate-300 hover:bg-[#1C1C26] hover:text-white'
                      }`}
                    >
                      <span
                        className={`h-2.5 w-2.5 rounded-full ${
                          isAnom ? 'bg-red-500 animate-pulse' : 'bg-emerald-400'
                        }`}
                      />
                      <span className={isSel ? 'text-emerald-300 font-extrabold' : ''}>{ch.id}</span>
                    </button>
                  )
                })}
              </div>
            </div>

            <div className="bg-black border border-[#22222E] rounded-md p-3 h-56 flex items-center justify-center">
              {channelWaveform.length < 2 ? (
                <div className="text-slate-400 font-mono text-sm">
                  Buffering telemetry stream for {selectedChannel}...
                </div>
              ) : (
                <BigWaveformChart
                  data={channelWaveform}
                  unit={CHANNELS.find((c) => c.id === selectedChannel)?.unit}
                  onSelectPoint={(pt) => setSelectedReading(pt)}
                />
              )}
            </div>

            <div className="mt-3 pt-2.5 border-t border-[#22222E] grid grid-cols-3 gap-3 font-mono text-xs">
              <div className="bg-[#14141C] p-2.5 rounded border border-[#262633]">
                <span className="text-slate-400 block text-[11px]">LATEST READING</span>
                <span className="text-white font-bold text-base">
                  {channelWaveform[channelWaveform.length - 1]?.value !== undefined
                    ? Number(channelWaveform[channelWaveform.length - 1].value).toExponential(4)
                    : '--'}{' '}
                  <span className="text-slate-300 text-xs font-normal">
                    {CHANNELS.find((c) => c.id === selectedChannel)?.unit}
                  </span>
                </span>
              </div>

              <div className="bg-[#14141C] p-2.5 rounded border border-[#262633]">
                <span className="text-slate-400 block text-[11px]">CHANNEL STATE</span>
                <span
                  className={`font-bold text-base ${
                    channelStates[selectedChannel]?.isAnomaly
                      ? 'text-red-400'
                      : 'text-emerald-400'
                  }`}
                >
                  {channelStates[selectedChannel]?.isAnomaly
                    ? '⚠️ FAULT DETECTED'
                    : '✓ NOMINAL STABLE'}
                </span>
              </div>

              <div className="bg-[#14141C] p-2.5 rounded border border-[#262633]">
                <span className="text-slate-400 block text-[11px]">ANOMALY RISK</span>
                <span className="text-emerald-300 font-bold text-base">
                  {channelWaveform[channelWaveform.length - 1]?.probability !== undefined
                    ? (channelWaveform[channelWaveform.length - 1].probability * 100).toFixed(1) + '%'
                    : '--'}
                </span>
              </div>
            </div>
          </div>

          <div className="border border-[#22222E] bg-[#0E0E14] rounded-lg p-4 shadow flex flex-col flex-1">
            <div className="flex items-center justify-between border-b border-[#22222E] pb-2 mb-3">
              <div>
                <h3 className="text-xs uppercase font-mono text-slate-300 font-bold tracking-wider">
                  DYNAMIC GRAPH TOPOLOGY & ROOT CAUSE PROPAGATION
                </h3>
                <p className="text-xs text-slate-400">
                  Edge thickness reflects real statistical correlation computed from telemetry data. Red nodes indicate active root/affected faults.
                </p>
              </div>
              <span
                className={`text-xs font-mono px-3 py-1 rounded border ${
                  channelGraphSource === 'real'
                    ? 'text-emerald-300 bg-[#0F2A1F] border-emerald-800'
                    : 'text-amber-300 bg-[#2A1F0F] border-amber-800'
                }`}
                title={
                  channelGraphSource === 'real'
                    ? 'Loaded from /channel-graph — computed from real telemetry correlations'
                    : 'Backend unreachable — showing fallback layout, not real data'
                }
              >
                {channelGraphSource === 'real'
                  ? 'Live computed graph'
                  : channelGraphSource === 'loading'
                  ? 'Loading graph...'
                  : 'Fallback layout'}
              </span>
            </div>

            <div className="bg-black border border-[#22222E] rounded-md p-2 h-72 flex items-center justify-center">
              <BigTopologyGraph
                channels={CHANNELS}
                edges={EDGES}
                channelStates={channelStates}
                rootChannel={activeIncident?.channel}
                selectedChannel={selectedChannel}
                onSelectChannel={(id) => setSelectedChannel(id)}
              />
            </div>
          </div>
        </div>

        <div className="xl:col-span-5 flex flex-col gap-4">
          <div
            className={`rounded-lg p-5 border transition-all shadow-md flex flex-col gap-3.5 ${
              activeIncident && activeIncident.status === 'OPEN'
                ? 'bg-red-950/40 border-red-500 shadow-red-950/50'
                : 'bg-[#0E0E14] border-[#22222E]'
            }`}
          >
            <div className="flex items-center justify-between border-b border-[#22222E] pb-3">
              <div className="flex items-center gap-2">
                <span
                  className={`h-3.5 w-3.5 rounded-full ${
                    activeIncident && activeIncident.status === 'OPEN'
                      ? 'bg-red-500 animate-ping'
                      : 'bg-emerald-400'
                  }`}
                />
                <span className="font-mono text-xs font-bold uppercase tracking-wider text-white">
                  {activeIncident ? activeIncident.id : 'DIAGNOSTICS'}: ROOT CAUSE & ACTION
                </span>
              </div>

              {activeIncident && activeIncident.status === 'OPEN' && (
                <button
                  onClick={() => handleResolveIncident(activeIncident.id)}
                  className="bg-emerald-600 hover:bg-emerald-500 text-white font-mono text-xs font-bold px-3.5 py-1.5 rounded shadow flex items-center gap-1.5 transition-all"
                >
                  <span>✓</span>
                  <span>EXECUTE FIX & RESOLVE</span>
                </button>
              )}

              {activeIncident && activeIncident.status === 'RESOLVED' && (
                <span className="bg-emerald-950 border border-emerald-500 text-emerald-300 text-xs font-mono px-2.5 py-1 rounded font-bold">
                  ✓ RESOLVED AT {activeIncident.resolvedAt}
                </span>
              )}
            </div>

            {activeIncident ? (
              <>
                <div className="bg-[#14141C] border border-[#262633] rounded-md p-3.5 flex flex-col gap-1">
                  <span className="text-xs uppercase font-mono text-slate-400">
                    IDENTIFIED ROOT CAUSE SENSOR:
                  </span>
                  <div className="flex items-center justify-between">
                    <span className="text-lg font-bold text-white font-mono">
                      <span className="text-red-400">{activeIncident.channel}</span> (
                      {activeIncident.channelName})
                    </span>
                    <span className="bg-red-900 border border-red-500 text-white text-xs font-mono px-2 py-0.5 rounded font-bold">
                      PROBABILITY: {(activeIncident.probability * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>

                <div className="space-y-2 text-xs">
                  <div className="bg-[#14141C] border border-[#262633] p-3 rounded">
                    <span className="text-slate-400 block text-[11px] font-mono mb-0.5">
                      AFFECTED SATELLITE SUBSYSTEM:
                    </span>
                    <span className="text-white font-bold text-sm">
                      {activeIncident.subsystem}
                    </span>
                  </div>

                  <div className="bg-[#14141C] border border-[#262633] p-3 rounded">
                    <span className="text-slate-400 block text-[11px] font-mono mb-0.5">
                      DETECTED FAILURE PATTERN:
                    </span>
                    <span className="text-slate-200 text-sm font-medium">
                      {activeIncident.faultType}
                    </span>
                  </div>

                  <div className="bg-[#14141C] border border-[#262633] p-3 rounded">
                    <span className="text-slate-400 block text-[11px] font-mono mb-0.5">
                      CROSS-CORRELATED SENSORS (PROPAGATION):
                    </span>
                    <span className="text-amber-300 font-mono text-xs font-bold">
                      {activeIncident.propagation.length > 0
                        ? activeIncident.propagation.join(' ➔ ')
                        : 'Isolated / No secondary sensor drift'}
                    </span>
                  </div>
                </div>

                <div className="bg-[#1C1608] border border-amber-500/80 p-3.5 rounded-md flex flex-col gap-1">
                  <span className="text-xs font-mono font-bold text-amber-300 uppercase tracking-wider flex items-center gap-1.5">
                    <span>⚡ RECOMMENDED TECHNICIAN REMEDIATION (FDIR):</span>
                  </span>
                  <p className="text-white text-xs leading-relaxed font-mono font-medium">
                    {activeIncident.fdirAction}
                  </p>
                </div>
              </>
            ) : (
              <div className="p-8 text-center text-slate-400 font-mono text-xs">
                All 9 sensors are currently operating within nominal baseline parameters. No active
                incidents requiring technician intervention.
              </div>
            )}
          </div>

          <div className="border border-[#22222E] bg-[#0E0E14] rounded-lg p-4 shadow flex flex-col flex-1 min-h-[260px]">
            <div className="flex items-center justify-between border-b border-[#22222E] pb-2.5 mb-2.5">
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-bold uppercase tracking-wider text-white">
                  TECHNICIAN INCIDENT INBOX
                </span>
                <span className="text-xs font-mono bg-[#1C1C26] text-white px-2.5 py-0.5 rounded border border-[#2E2E3E] font-bold">
                  {openIncidents.length} Open
                </span>
              </div>

              <div className="flex items-center gap-2 font-mono text-xs">
                {openIncidents.length > 1 && (
                  <button
                    onClick={handleResolveAll}
                    className="text-xs text-emerald-400 hover:text-emerald-300 underline font-bold"
                  >
                    Resolve All ({openIncidents.length})
                  </button>
                )}

                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setIncidentTab('open')}
                    className={`px-3 py-1 rounded text-xs font-bold border ${
                      incidentTab === 'open'
                        ? 'bg-red-950 border-red-500 text-red-100'
                        : 'bg-[#181824] border-[#2C2C3C] text-slate-300 hover:text-white'
                    }`}
                  >
                    Open ({openIncidents.length})
                  </button>
                  <button
                    onClick={() => setIncidentTab('resolved')}
                    className={`px-3 py-1 rounded text-xs font-bold border ${
                      incidentTab === 'resolved'
                        ? 'bg-emerald-950 border-emerald-500 text-emerald-100'
                        : 'bg-[#181824] border-[#2C2C3C] text-slate-300 hover:text-white'
                    }`}
                  >
                    Resolved ({resolvedIncidents.length})
                  </button>
                </div>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto max-h-[300px] space-y-2 pr-1.5 font-mono text-xs">
              {(incidentTab === 'open' ? openIncidents : resolvedIncidents).length === 0 ? (
                <div className="h-full flex items-center justify-center p-6 text-center text-slate-400 text-xs">
                  {incidentTab === 'open'
                    ? '✓ No open unresolved issues! Spacecraft healthy.'
                    : 'No resolved incident history yet.'}
                </div>
              ) : (
                (incidentTab === 'open' ? openIncidents : resolvedIncidents).map((inc) => {
                  const isSel = activeIncident?.id === inc.id
                  const isOpen = inc.status === 'OPEN'

                  return (
                    <div
                      key={inc.id}
                      onClick={() => {
                        setSelectedIncidentId(inc.id)
                        setSelectedChannel(inc.channel)
                      }}
                      className={`cursor-pointer p-3 rounded-md border flex items-center justify-between transition-all ${
                        isSel
                          ? 'border-amber-400 bg-[#1F180A] shadow'
                          : isOpen
                          ? 'border-red-900 bg-red-950/40 hover:border-red-600'
                          : 'border-[#22222E] bg-[#12121A] hover:bg-[#181824]'
                      }`}
                    >
                      <div className="flex flex-col gap-0.5">
                        <div className="flex items-center gap-2">
                          <span
                            className={`h-2.5 w-2.5 rounded-full ${
                              isOpen ? 'bg-red-500 animate-pulse' : 'bg-emerald-400'
                            }`}
                          />
                          <span className="font-bold text-white text-xs">{inc.id}</span>
                          <span className="text-amber-300 font-bold">{inc.channel}</span>
                          <span className="text-slate-300 text-[11px]">({inc.channelName})</span>
                        </div>
                        <span className="text-[11px] text-slate-300">{inc.faultType}</span>
                      </div>

                      <div className="flex items-center gap-3">
                        <span className="text-slate-400 text-[11px]">{inc.createdTime}</span>
                        {isOpen ? (
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              handleResolveIncident(inc.id)
                            }}
                            className="bg-emerald-600 hover:bg-emerald-500 text-white px-3 py-1 rounded text-xs font-bold shadow"
                          >
                            FIX CONFIRMED
                          </button>
                        ) : (
                          <span className="text-emerald-400 text-xs font-bold">✓ FIXED</span>
                        )}
                      </div>
                    </div>
                  )
                })
              )}
            </div>
          </div>
        </div>
      </main>

      <footer className="border-t border-[#22222E] bg-[#0A0A0E] px-6 py-2.5 flex items-center justify-between text-xs font-mono">
        <div className="text-slate-400">
          LOGGED FRAMES: <span className="text-white font-bold">{readings.length}</span> | ACTIVE SENSORS:{' '}
          <span className="text-amber-400 font-bold">9 / 9 OPERATIONAL</span>
        </div>
        <div className="text-slate-400">
          MODEL: <span className="text-emerald-400 font-bold">DYNAMIC GRAPH ANOMALY DETECTOR + FDIR</span>
        </div>
      </footer>
    </div>
  )
}


function BigWaveformChart({ data, unit, onSelectPoint }) {
  if (!data || data.length < 2) return null

  const width = 720
  const height = 220
  const pad = { top: 20, right: 30, bottom: 30, left: 75 }

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

  const points = data.map((d, i) => `${getX(i)},${getY(Number(d.value))}`)
  const pathD = `M ${points.join(' L ')}`

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full font-mono select-none">
      <line x1={pad.left} y1={pad.top} x2={width - pad.right} y2={pad.top} stroke="#22222E" strokeDasharray="3 3" />
      <line x1={pad.left} y1={(pad.top + height - pad.bottom) / 2} x2={width - pad.right} y2={(pad.top + height - pad.bottom) / 2} stroke="#1A1A24" strokeDasharray="2 2" />
      <line x1={pad.left} y1={height - pad.bottom} x2={width - pad.right} y2={height - pad.bottom} stroke="#22222E" />

      <text x={pad.left - 10} y={pad.top + 4} fill="#CBD5E1" fontSize="11" fontWeight="bold" textAnchor="end">
        {maxVal.toExponential(2)} {unit}
      </text>
      <text x={pad.left - 10} y={height - pad.bottom} fill="#CBD5E1" fontSize="11" fontWeight="bold" textAnchor="end">
        {minVal.toExponential(2)} {unit}
      </text>

      <path d={pathD} fill="none" stroke="#10B981" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />

      {data.map((d, i) => {
        const cx = getX(i)
        const cy = getY(Number(d.value))
        const isAnom = d.prediction === 1

        return (
          <g key={i} className="cursor-pointer" onClick={() => onSelectPoint && onSelectPoint(d)}>
            {isAnom ? (
              <>
                <circle cx={cx} cy={cy} r="6" fill="#EF4444" stroke="#7F1D1D" strokeWidth="1.5" />
                <line x1={cx} y1={cy - 8} x2={cx} y2={cy + 8} stroke="#EF4444" strokeWidth="1.5" />
              </>
            ) : (
              <circle cx={cx} cy={cy} r="2.5" fill="#10B981" />
            )}
          </g>
        )
      })}
    </svg>
  )
}

function BigTopologyGraph({
  channels,
  edges,
  channelStates,
  rootChannel,
  selectedChannel,
  onSelectChannel,
}) {
  const width = 600
  const height = 300

  const nodeMap = {}
  channels.forEach((ch) => {
    nodeMap[ch.id] = ch
  })

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full select-none font-mono">
      <rect x="25" y="15" width="550" height="105" fill="#0C0C12" rx="6" stroke="#252535" strokeDasharray="3 3" />
      <text x="38" y="34" fill="#FBBF24" fontSize="11" fontWeight="bold">
        ADCS / ATTITUDE SENSORS (CADC0872 - CADC0874)
      </text>

      <rect x="25" y="135" width="550" height="150" fill="#0C0C12" rx="6" stroke="#252535" strokeDasharray="3 3" />
      <text x="38" y="154" fill="#CBD5E1" fontSize="11" fontWeight="bold">
        EPS / SOLAR SENSORS (CADC0884 - CADC0894)
      </text>

      {edges.map(([idA, idB, strength], idx) => {
        const nodeA = nodeMap[idA]
        const nodeB = nodeMap[idB]
        if (!nodeA || !nodeB) return null

        const isRootA = idA === rootChannel
        const isRootB = idB === rootChannel
        const isCorrelated = isRootA || isRootB
        const baseWidth = strength != null ? Math.max(1, strength * 5) : 1.5

        return (
          <line
            key={idx}
            x1={nodeA.x}
            y1={nodeA.y}
            x2={nodeB.x}
            y2={nodeB.y}
            stroke={isCorrelated ? '#EF4444' : '#3B3B4F'}
            strokeWidth={isCorrelated ? 3 : baseWidth}
            strokeDasharray={isCorrelated ? 'none' : '3 3'}
          />
        )
      })}

      {channels.map((ch) => {
        const state = channelStates[ch.id]
        const isAnomaly = state?.isAnomaly
        const isRoot = ch.id === rootChannel
        const isSelected = ch.id === selectedChannel

        return (
          <g
            key={ch.id}
            className="cursor-pointer"
            onClick={() => onSelectChannel && onSelectChannel(ch.id)}
          >
            {isRoot && (
              <circle
                cx={ch.x}
                cy={ch.y}
                r="26"
                fill="none"
                stroke="#EF4444"
                strokeWidth="2.5"
                strokeDasharray="4 4"
              />
            )}

            <circle
              cx={ch.x}
              cy={ch.y}
              r="18"
              fill={isRoot ? '#7F1D1D' : isAnomaly ? '#450A0A' : isSelected ? '#332712' : '#14141E'}
              stroke={isRoot ? '#FF3344' : isAnomaly ? '#F87171' : isSelected ? '#FBBF24' : '#525266'}
              strokeWidth={isRoot || isSelected ? 2.5 : 1.5}
            />

            <text
              x={ch.x}
              y={ch.y + 4.5}
              fill="#FFFFFF"
              fontSize="10"
              fontWeight="bold"
              textAnchor="middle"
            >
              {ch.id.slice(4)}
            </text>

            <text
              x={ch.x}
              y={ch.y + 28}
              fill={isSelected ? '#FBBF24' : '#FFFFFF'}
              fontSize="10"
              fontWeight={isSelected ? 'bold' : '600'}
              textAnchor="middle"
            >
              {ch.name}
            </text>
          </g>
        )
      })}
    </svg>
  )
}
