import { useState } from 'react';

export default function UrlInput({ onAnalyze, loading }) {
  const [url, setUrl] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (url.trim()) {
      onAnalyze(url.trim());
    }
  };

  return (
    <form onSubmit={handleSubmit} className="url-input">
      <div className="input-group">
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://wokwi.com/projects/..."
          disabled={loading}
          required
        />
        <button type="submit" disabled={loading || !url.trim()}>
          {loading ? (
            <>
              <span className="spinner"></span>
              Analyzing...
            </>
          ) : (
            'Analyze Circuit'
          )}
        </button>
      </div>
      <p className="hint">Paste a public Wokwi project URL to analyze it for circuit and code faults</p>
    </form>
  );
}
