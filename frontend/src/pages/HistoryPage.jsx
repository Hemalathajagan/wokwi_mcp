import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getHistory, deleteHistoryItem } from '../api';

export default function HistoryPage() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchHistory = async () => {
    try {
      const data = await getHistory();
      setHistory(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const handleDelete = async (id) => {
    try {
      await deleteHistoryItem(id);
      setHistory((prev) => prev.filter((item) => item.id !== id));
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  const parseSummary = (summaryJson) => {
    try {
      return JSON.parse(summaryJson);
    } catch {
      return null;
    }
  };

  if (loading) {
    return (
      <div className="auth-loading">
        <div className="spinner" />
        <p>Loading history...</p>
      </div>
    );
  }

  return (
    <div className="history-page">
      <h2>Analysis History</h2>

      {error && <div className="error-banner">{error}</div>}

      {history.length === 0 ? (
        <div className="history-empty">
          <p>No analyses yet. Go to the dashboard and analyze a Wokwi or KiCad project.</p>
        </div>
      ) : (
        <div className="history-list">
          {history.map((item) => {
            const summary = parseSummary(item.summary_json);
            const isKiCad = item.project_type === 'kicad';
            return (
              <div key={item.id} className="history-card">
                <div className="history-card-header">
                  <div className="history-card-info">
                    <div className="history-card-title-row">
                      <span className={`project-type-badge ${isKiCad ? 'kicad' : 'wokwi'}`}>
                        {isKiCad ? 'KiCad' : 'Wokwi'}
                      </span>
                      {isKiCad ? (
                        <span className="history-project-name">
                          {item.project_name || 'KiCad Project'}
                        </span>
                      ) : (
                        <a
                          href={item.wokwi_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="history-url"
                        >
                          {item.wokwi_url}
                        </a>
                      )}
                    </div>
                    <span className="history-date">
                      {new Date(item.created_at).toLocaleString()}
                    </span>
                  </div>
                  <div className="history-card-actions">
                    <Link to={`/history/${item.id}`} className="history-view-btn">
                      View Report
                    </Link>
                    <button
                      className="history-delete-btn"
                      onClick={() => handleDelete(item.id)}
                      title="Delete"
                    >
                      Delete
                    </button>
                  </div>
                </div>
                <div className="history-card-stats">
                  <span className="history-fault-count">
                    {item.fault_count} fault{item.fault_count !== 1 ? 's' : ''}
                  </span>
                  {summary && (
                    <>
                      {summary.errors > 0 && (
                        <span className="history-stat error">{summary.errors} errors</span>
                      )}
                      {summary.warnings > 0 && (
                        <span className="history-stat warning">{summary.warnings} warnings</span>
                      )}
                      {summary.infos > 0 && (
                        <span className="history-stat info">{summary.infos} infos</span>
                      )}
                    </>
                  )}
                  {item.project_id && (
                    <span className="history-project-id">Project: {item.project_id}</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
