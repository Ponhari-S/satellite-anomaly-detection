// Day 24 (Prince) — Replace the hardcoded EDGES constant with real,
// computed channel correlations from the backend.
//
// WHAT CHANGES: instead of a fixed EDGES array made up by hand, the app
// now fetches actual correlation data (computed from real telemetry in
// ai/graph_model/graph_construction.py) once on load, and uses it to
// decide which channels to connect AND how strongly (edge thickness).
//
// HOW TO APPLY: add this near the top of App.jsx (after the CHANNELS
// constant), and replace the old hardcoded `const EDGES = [...]` block
// entirely with the fetch logic below.

import { useState, useEffect } from 'react'

// ... (keep the existing CHANNELS array as-is) ...

// REMOVE the old hardcoded EDGES array entirely. Replace with:

function useChannelGraph() {
  const [edges, setEdges] = useState([])       // real edges: [{source, target, strength}]
  const [graphSource, setGraphSource] = useState('loading') // 'real' | 'fallback' | 'loading'

  useEffect(() => {
    fetch('http://127.0.0.1:8000/channel-graph')
      .then((res) => res.json())
      .then((data) => {
        // Convert {source, target, strength} objects into the [a, b] pair
        // format the existing BigTopologyGraph component expects, but also
        // keep the strength value available for edge-thickness rendering.
        const formatted = data.edges.map((e) => [e.source, e.target, e.strength])
        setEdges(formatted)
        setGraphSource('real')
        console.log(`[channel-graph] loaded ${formatted.length} real, computed edges`)
      })
      .catch((err) => {
        console.error('[channel-graph] failed to load real edges, using fallback:', err)
        // Fallback only if the backend endpoint is unreachable — never
        // silently pretend fabricated data is real.
        setEdges([
          ['CADC0872', 'CADC0873'], ['CADC0884', 'CADC0890'],
        ])
        setGraphSource('fallback')
      })
  }, [])

  return { edges, graphSource }
}

// Inside the App() component, replace any reference to the old EDGES
// constant with:
//
//   const { edges: EDGES, graphSource } = useChannelGraph()
//
// And show the user which mode is active (important for demo honesty —
// never let the graph look "real" if it's actually the fallback):
//
//   <span className="text-xs font-mono text-slate-400">
//     Topology: {graphSource === 'real' ? 'Computed from telemetry data' : 'Fallback layout'}
//   </span>
//
// In BigTopologyGraph, edge thickness can now reflect real strength
// instead of a fixed strokeWidth, e.g.:
//
//   strokeWidth={isCorrelated ? 3 : Math.max(1, (edgeStrength || 0.1) * 6)}
//
// where edgeStrength comes from the third element of each EDGES tuple.