import { useState, useEffect } from 'react'

function App() {
  const [health, setHealth] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch('http://127.0.0.1:8000/health')
      .then((res) => res.json())
      .then((data) => setHealth(data))
      .catch((err) => setError(err.message))
  }, [])

  return (
    <div style={{ padding: '2rem', fontFamily: 'sans-serif' }}>
      <h1>Satellite Anomaly Detection — Frontend Scaffold</h1>
      <p>Day 21: blank project confirmed running. Day 22 target: connect to backend.</p>
      <h2>Backend connectivity check</h2>
      {error && <p style={{ color: 'red' }}>Error connecting to backend: {error}</p>}
      {health && <pre>{JSON.stringify(health, null, 2)}</pre>}
      {!health && !error && <p>Connecting to backend at http://127.0.0.1:8000/health ...</p>}
    </div>
  )
}

export default App
