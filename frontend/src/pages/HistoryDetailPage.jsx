import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getHistoryItem } from '../api';
import SummaryBar from '../components/SummaryBar';
import FaultReport from '../components/FaultReport';
import CircuitViewer from '../components/CircuitViewer';
import CodeView from '../components/CodeView';
import FixSuggestion from '../components/FixSuggestion';

export default function HistoryDetailPage() {
  const { id } = useParams();
  const [report, setReport] = useState(null);
  const [meta, setMeta] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeSection, setActiveSection] = useState('faults');

  useEffect(() => {
    const load = async () => {
      try {
        const item = await getHistoryItem(id);
        setMeta(item);
        if (item.report_json) {
          setReport(JSON.parse(item.report_json));
        } else {
          setError('Full report data is not available for this entry.');
        }
      } catch (err) {
        setError(err.response?.data?.detail || err.message);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [id]);

  if (loading) {
    return (
      <div className="auth-loading">
        <div className="spinner" />
        <p>Loading report...</p>
      </div>
    );
  }

  return (
    <div className="history-detail-page">
      <Link to="/history" className="back-link">Back to History</Link>

      {meta && (
        <div className="history-detail-header">
          <h2>Analysis Report</h2>
          <p className="history-detail-meta">
            <a href={meta.wokwi_url} target="_blank" rel="noopener noreferrer">{meta.wokwi_url}</a>
            {' '} — {new Date(meta.created_at).toLocaleString()}
          </p>
        </div>
      )}

      {error && <div className="error-banner"><strong>Error:</strong> {error}</div>}

      {report && (
        <>
          <SummaryBar summary={report.summary} />

          <nav className="section-nav">
            {['faults', 'circuit', 'code', 'fix'].map((section) => (
              <button
                key={section}
                className={activeSection === section ? 'active' : ''}
                onClick={() => setActiveSection(section)}
              >
                {section === 'faults' && 'Fault Report'}
                {section === 'circuit' && 'Circuit'}
                {section === 'code' && 'Code'}
                {section === 'fix' && 'Fix Suggestions'}
              </button>
            ))}
          </nav>

          <div className="section-content">
            {activeSection === 'faults' && <FaultReport faults={report.faults} />}
            {activeSection === 'circuit' && <CircuitViewer diagram={report.diagram} />}
            {activeSection === 'code' && (
              <CodeView sketchCode={report.sketch_code} faults={report.faults} />
            )}
            {activeSection === 'fix' && <FixSuggestion report={report} />}
          </div>
        </>
      )}
    </div>
  );
}
