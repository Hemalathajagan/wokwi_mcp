import { useState } from 'react';

const CATEGORY_LABELS = {
  wiring: 'Wiring',
  component: 'Component',
  power: 'Power',
  signal: 'Signal',
  code: 'Code',
  cross_reference: 'Code-Circuit',
  system: 'System',
  intent_mismatch: 'Intent Mismatch',
  erc: 'ERC',
  drc: 'DRC',
  connectivity: 'Connectivity',
  manufacturing: 'Manufacturing',
  thermal: 'Thermal',
  emc: 'EMC',
};

const SEVERITY_COLORS = {
  error: '#ef4444',
  warning: '#f59e0b',
  info: '#3b82f6',
};

export default function FaultReport({ faults }) {
  const [expandedIndex, setExpandedIndex] = useState(null);
  const [filterCategory, setFilterCategory] = useState('all');

  if (!faults || faults.length === 0) {
    return (
      <div className="fault-report">
        <h2>Fault Report</h2>
        <div className="no-faults">No issues detected! The circuit looks good.</div>
      </div>
    );
  }

  // Group by category
  const categories = [...new Set(faults.map((f) => f.category))];
  const filtered = filterCategory === 'all'
    ? faults
    : faults.filter((f) => f.category === filterCategory);

  return (
    <div className="fault-report">
      <h2>Fault Report</h2>

      <div className="category-filters">
        <button
          className={filterCategory === 'all' ? 'active' : ''}
          onClick={() => setFilterCategory('all')}
        >
          All ({faults.length})
        </button>
        {categories.map((cat) => (
          <button
            key={cat}
            className={filterCategory === cat ? 'active' : ''}
            onClick={() => setFilterCategory(cat)}
          >
            {CATEGORY_LABELS[cat] || cat} ({faults.filter((f) => f.category === cat).length})
          </button>
        ))}
      </div>

      <div className="fault-list">
        {filtered.map((fault, i) => {
          const globalIndex = faults.indexOf(fault);
          const isExpanded = expandedIndex === globalIndex;

          return (
            <div
              key={globalIndex}
              className={`fault-card ${fault.severity}`}
              onClick={() => setExpandedIndex(isExpanded ? null : globalIndex)}
            >
              <div className="fault-header">
                <span
                  className="severity-badge"
                  style={{ backgroundColor: SEVERITY_COLORS[fault.severity] || '#6b7280' }}
                >
                  {fault.severity?.toUpperCase()}
                </span>
                <span className="category-badge">
                  {CATEGORY_LABELS[fault.category] || fault.category}
                </span>
                <span className="fault-title">{fault.title}</span>
                <span className="component-tag">{fault.component}</span>
                <span className="expand-icon">{isExpanded ? '\u25B2' : '\u25BC'}</span>
              </div>

              {isExpanded && (
                <div className="fault-details">
                  <div className="detail-section">
                    <h4>Why is this a problem?</h4>
                    <p>{fault.explanation}</p>
                  </div>
                  {fault.fix && (
                    <div className="detail-section fix">
                      <h4>Suggested Fix</h4>
                      <p><strong>Type:</strong> {fault.fix.type}</p>
                      <p>{fault.fix.description}</p>
                      {fault.fix.corrected_snippet && (
                        <pre className="code-snippet">{fault.fix.corrected_snippet}</pre>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
