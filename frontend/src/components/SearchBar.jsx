import { useState, useEffect } from 'react'

const PLATFORM_OPTIONS = [
  { id: 'youtube', name: 'YouTube', icon: '🎥' },
  { id: 'github', name: 'GitHub', icon: '💻' },
  { id: 'reddit', name: 'Reddit', icon: '🗨️' },
  { id: 'twitter', name: 'Twitter/X', icon: '🐦' },
  { id: 'blogs', name: 'Blogs', icon: '📝' },
  { id: 'linkedin', name: 'LinkedIn', icon: '💼' },
  { id: 'facebook', name: 'Facebook', icon: '👥' },
  { id: 'instagram', name: 'Instagram', icon: '📸' },
  { id: 'quora', name: 'Quora', icon: '❓' },
  { id: 'events', name: 'Events', icon: '📅' }
]

export default function SearchBar({ onSearch, isLoading }) {
  const [topic, setTopic] = useState('')
  const [selectedPlatforms, setSelectedPlatforms] = useState([])
  const [showOptions, setShowOptions] = useState(false)

  // Select all platforms by default
  useEffect(() => {
    setSelectedPlatforms(PLATFORM_OPTIONS.map(p => p.id))
  }, [])

  const togglePlatform = (platformId) => {
    setSelectedPlatforms(prev =>
      prev.includes(platformId)
        ? prev.filter(id => id !== platformId)
        : [...prev, platformId]
    )
  }

  const selectAll = () => {
    setSelectedPlatforms(PLATFORM_OPTIONS.map(p => p.id))
  }

  const deselectAll = () => {
    setSelectedPlatforms([])
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (topic.trim() && !isLoading && selectedPlatforms.length > 0) {
      onSearch({
        topic: topic.trim(),
        sources: selectedPlatforms
      })
    }
  }

  return (
    <div className="search-container">
      <form onSubmit={handleSubmit}>
        <div className="search-input-wrapper">
          <input
            type="text"
            className="search-input"
            placeholder="Enter any topic... (e.g., Machine Learning, Yoga, Blockchain)"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            disabled={isLoading}
          />
          <button
            type="button"
            className="options-toggle"
            onClick={() => setShowOptions(!showOptions)}
            disabled={isLoading}
            title="Search Options"
          >
            ⚙️
          </button>
        </div>

        {showOptions && (
          <div className="search-options">
            {/* Platform Selection */}
            <div className="option-section">
              <div className="platform-header">
                <h4 className="option-title">
                  Select Platforms ({selectedPlatforms.length}/{PLATFORM_OPTIONS.length})
                </h4>
                <div className="platform-controls">
                  <button
                    type="button"
                    className="link-button"
                    onClick={selectAll}
                    disabled={isLoading}
                  >
                    Select All
                  </button>
                  <button
                    type="button"
                    className="link-button"
                    onClick={deselectAll}
                    disabled={isLoading}
                  >
                    Clear All
                  </button>
                </div>
              </div>

              <div className="platform-grid">
                {PLATFORM_OPTIONS.map(platform => (
                  <label
                    key={platform.id}
                    className={`platform-option ${selectedPlatforms.includes(platform.id) ? 'selected' : ''}`}
                  >
                    <input
                      type="checkbox"
                      checked={selectedPlatforms.includes(platform.id)}
                      onChange={() => togglePlatform(platform.id)}
                      disabled={isLoading}
                    />
                    <span className="platform-icon">{platform.icon}</span>
                    <span className="platform-name">{platform.name}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>
        )}

        <button
          type="submit"
          className="search-button"
          disabled={isLoading || !topic.trim() || selectedPlatforms.length === 0}
        >
          {isLoading ? 'Searching...' : `Explore ${selectedPlatforms.length > 0 ? `${selectedPlatforms.length} Platform${selectedPlatforms.length !== 1 ? 's' : ''}` : ''}`}
        </button>

        {selectedPlatforms.length === 0 && (
          <p className="warning-text">⚠️ Please select at least one platform</p>
        )}
      </form>
    </div>
  )
}
