import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getHistoryItem } from '../api';
import SummaryBar from '../components/SummaryBar';
import FaultReport from '../components/FaultReport';
import CircuitViewer from '../components/CircuitViewer';
import SchematicViewer from '../components/SchematicViewer';
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

  const projectType = report?.project_type || meta?.project_type || 'wokwi';
  const isKiCad = projectType === 'kicad';

  const tabs = isKiCad
    ? [
        { key: 'faults', label: 'Fault Report' },
        { key: 'schematic', label: 'Project Info' },
        { key: 'fix', label: 'Fix Suggestions' },
      ]
    : [
        { key: 'faults', label: 'Fault Report' },
        { key: 'circuit', label: 'Circuit' },
        { key: 'code', label: 'Code' },
        { key: 'fix', label: 'Fix Suggestions' },
      ];

  return (
    <div className="history-detail-page">
      <Link to="/history" className="back-link">Back to History</Link>

      {meta && (
        <div className="history-detail-header">
          <h2>
            Analysis Report
            <span className={`project-type-badge ${isKiCad ? 'kicad' : 'wokwi'}`} style={{ marginLeft: '0.75rem', fontSize: '0.75rem', verticalAlign: 'middle' }}>
              {isKiCad ? 'KiCad' : 'Wokwi'}
            </span>
          </h2>
          <p className="history-detail-meta">
            {isKiCad ? (
              <span>{meta.project_name || 'KiCad Project'}</span>
            ) : (
              <a href={meta.wokwi_url} target="_blank" rel="noopener noreferrer">{meta.wokwi_url}</a>
            )}
            {' '} — {new Date(meta.created_at).toLocaleString()}
          </p>
        </div>
      )}

      {error && <div className="error-banner"><strong>Error:</strong> {error}</div>}

      {report && (
        <>
          <SummaryBar summary={report.summary} />

          <nav className="section-nav">
            {tabs.map(({ key, label }) => (
              <button
                key={key}
                className={activeSection === key ? 'active' : ''}
                onClick={() => setActiveSection(key)}
              >
                {label}
              </button>
            ))}
          </nav>

          <div className="section-content">
            {activeSection === 'faults' && <FaultReport faults={report.faults} />}
            {activeSection === 'circuit' && !isKiCad && (
              <CircuitViewer diagram={report.diagram} />
            )}
            {activeSection === 'schematic' && isKiCad && (
              <SchematicViewer report={report} />
            )}
            {activeSection === 'code' && !isKiCad && (
              <CodeView sketchCode={report.sketch_code} faults={report.faults} />
            )}
            {activeSection === 'fix' && (
              <FixSuggestion report={report} projectType={projectType} />
            )}
          </div>
        </>
      )}
    </div>
  );
}
