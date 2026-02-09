import { useState } from 'react';
import { suggestFix } from '../api';

export default function FixSuggestion({ report }) {
  const [fixResult, setFixResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  if (!report || !report.faults || report.faults.length === 0) return null;

  const handleGenerateFix = async () => {
    setLoading(true);
    setError(null);
    try {
      const faultReport = JSON.stringify(report.faults, null, 2);
      const diagramJson = report.diagram ? JSON.stringify(report.diagram) : '';
      const result = await suggestFix(faultReport, diagramJson, report.sketch_code || '');
      if (result.error) {
        setError(result.error);
      } else {
        setFixResult(result);
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fix-suggestion">
      <h2>Fix Suggestions</h2>

      {!fixResult && (
        <button
          onClick={handleGenerateFix}
          disabled={loading}
          className="generate-fix-btn"
        >
          {loading ? (
            <>
              <span className="spinner"></span>
              Generating fixes...
            </>
          ) : (
            'Generate Corrected Code & Wiring'
          )}
        </button>
      )}

      {error && <div className="error-message">{error}</div>}

      {fixResult && (
        <div className="fix-results">
          {fixResult.summary && (
            <div className="fix-summary">
              <h3>Summary of Changes</h3>
              <p>{fixResult.summary}</p>
            </div>
          )}

          {fixResult.wiring_changes && fixResult.wiring_changes.length > 0 && (
            <div className="fix-section">
              <h3>Wiring Changes</h3>
              {fixResult.wiring_changes.map((change, i) => (
                <div key={i} className="wiring-change">
                  <p>{change.description}</p>
                  {change.original && (
                    <div className="diff-line removed">- {change.original}</div>
                  )}
                  {change.corrected && (
                    <div className="diff-line added">+ {change.corrected}</div>
                  )}
                </div>
              ))}
            </div>
          )}

          {fixResult.corrected_code && (
            <div className="fix-section">
              <h3>Corrected Code</h3>
              <div className="code-container">
                <pre>{fixResult.corrected_code}</pre>
              </div>
              <button
                className="copy-btn"
                onClick={() => navigator.clipboard.writeText(fixResult.corrected_code)}
              >
                Copy Code
              </button>
            </div>
          )}

          {fixResult.corrected_connections && (
            <div className="fix-section">
              <h3>Corrected Connections</h3>
              <div className="code-container">
                <pre>{JSON.stringify(fixResult.corrected_connections, null, 2)}</pre>
              </div>
              <button
                className="copy-btn"
                onClick={() =>
                  navigator.clipboard.writeText(
                    JSON.stringify(fixResult.corrected_connections, null, 2)
                  )
                }
              >
                Copy Connections
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
