import { useState, useEffect, useRef } from 'react'
import SearchBar from './components/SearchBar'
import LoadingState from './components/LoadingState'
import InsightDashboard from './components/InsightDashboard'
import ResultTabs from './components/ResultTabs'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function App() {
  const [status, setStatus] = useState('idle') // idle, loading, done, error
  const [data, setData] = useState(null)
  const [progress, setProgress] = useState({ step: '', progress: 0 })
  const [error, setError] = useState(null)
  const pollIntervalRef = useRef(null)

  const clearPolling = () => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current)
      pollIntervalRef.current = null
    }
  }

  useEffect(() => {
    return () => clearPolling()
  }, [])

  const handleSearch = async (searchParams) => {
    const { topic, sources } = searchParams
    
    setStatus('loading')
    setData(null)
    setError(null)
    setProgress({ step: 'Starting search...', progress: 0 })
    clearPolling()

    try {
      // Start the search
      const response = await fetch(`${API_URL}/api/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic,
          sources: sources
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to start search')
      }

      const { job_id } = await response.json()

      // Poll for status
      pollIntervalRef.current = setInterval(async () => {
        try {
          const statusRes = await fetch(`${API_URL}/api/status/${job_id}`)
          const statusData = await statusRes.json()

          if (statusData.status === 'progress') {
            setProgress({
              step: statusData.step || 'Processing...',
              progress: statusData.progress || 0,
            })
          } else if (statusData.status === 'done') {
            clearPolling()
            setData({
              topic: statusData.topic,
              insights: statusData.insights,
              results: statusData.results,
              total_results: statusData.total_results,
              sources_searched: statusData.sources_searched
            })
            setStatus('done')
          } else if (statusData.status === 'error') {
            clearPolling()
            setError(statusData.error || 'An error occurred')
            setStatus('error')
          }
        } catch (err) {
          console.error('Polling error:', err)
        }
      }, 1000)

    } catch (err) {
      setError(err.message)
      setStatus('error')
    }
  }

  return (
    <div className="app-container">
      <header className="app-header">
        <h1 className="app-title">TopicLens</h1>
        <p className="app-subtitle">
          Discover curated resources about any topic from across the internet
        </p>
      </header>

      <SearchBar 
        onSearch={handleSearch} 
        isLoading={status === 'loading'}
      />

      {status === 'loading' && (
        <LoadingState step={progress.step} progress={progress.progress} />
      )}

      {status === 'error' && (
        <div className="error-container">
          <h3>Something went wrong</h3>
          <p>{error}</p>
          <button
            className="search-button"
            style={{ marginTop: '16px' }}
            onClick={() => setStatus('idle')}
          >
            Try Again
          </button>
        </div>
      )}

      {status === 'done' && data && (
        <>
          <InsightDashboard
            insights={data.insights}
            topic={data.topic}
            total={data.total_results}
          />
          <ResultTabs results={data.results} />
        </>
      )}

      {status === 'idle' && (
        <div className="empty-state">
          <div className="empty-icon">🔭</div>
          <p>Enter a topic above to start exploring</p>
          <p className="empty-hint">
            💡 Tip: Click the ⚙️ icon to choose platforms
          </p>
        </div>
      )}
    </div>
  )
}
