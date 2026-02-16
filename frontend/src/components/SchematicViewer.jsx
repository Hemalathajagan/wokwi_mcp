import { useState } from 'react';

export default function SchematicViewer({ report }) {
  const [activeTab, setActiveTab] = useState('overview');

  if (!report) return null;

  const info = report.schematic_info || {};
  const pcbInfo = report.pcb_info || null;
  const faults = report.faults || [];

  // Extract unique components and nets from faults for display
  const components = [...new Set(faults.map((f) => f.component).filter(Boolean))];
  const categories = {};
  faults.forEach((f) => {
    const cat = f.category || 'other';
    categories[cat] = (categories[cat] || 0) + 1;
  });

  return (
    <div className="circuit-viewer">
      <h2>Project Overview</h2>

      <div className="tabs">
        <button
          className={activeTab === 'overview' ? 'active' : ''}
          onClick={() => setActiveTab('overview')}
        >
          Overview
        </button>
        <button
          className={activeTab === 'components' ? 'active' : ''}
          onClick={() => setActiveTab('components')}
        >
          Components ({components.length})
        </button>
        <button
          className={activeTab === 'categories' ? 'active' : ''}
          onClick={() => setActiveTab('categories')}
        >
          Issue Breakdown
        </button>
      </div>

      {activeTab === 'overview' && (
        <div className="schematic-overview">
          <table className="data-table">
            <thead>
              <tr>
                <th>Metric</th>
                <th>Value</th>
              </tr>
            </thead>
            <tbody>
              {info.symbols_count != null && (
                <tr>
                  <td>Schematic Symbols</td>
                  <td><strong>{info.symbols_count}</strong></td>
                </tr>
              )}
              {info.nets_count != null && (
                <tr>
                  <td>Nets</td>
                  <td><strong>{info.nets_count}</strong></td>
                </tr>
              )}
              {info.power_symbols_count != null && (
                <tr>
                  <td>Power Symbols</td>
                  <td><strong>{info.power_symbols_count}</strong></td>
                </tr>
              )}
              {pcbInfo && (
                <>
                  <tr>
                    <td>PCB Footprints</td>
                    <td><strong>{pcbInfo.footprints_count}</strong></td>
                  </tr>
                  <tr>
                    <td>PCB Tracks</td>
                    <td><strong>{pcbInfo.segments_count}</strong></td>
                  </tr>
                  <tr>
                    <td>Vias</td>
                    <td><strong>{pcbInfo.vias_count}</strong></td>
                  </tr>
                  <tr>
                    <td>Copper Zones</td>
                    <td><strong>{pcbInfo.zones_count}</strong></td>
                  </tr>
                </>
              )}
              <tr>
                <td>Project Name</td>
                <td><code>{report.project_name || 'N/A'}</code></td>
              </tr>
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'components' && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Reference</th>
              <th>Issues</th>
            </tr>
          </thead>
          <tbody>
            {components.length === 0 ? (
              <tr>
                <td colSpan={2} style={{ textAlign: 'center', color: '#6b7280' }}>
                  No component-specific issues found
                </td>
              </tr>
            ) : (
              components.map((comp) => {
                const count = faults.filter((f) => f.component === comp).length;
                return (
                  <tr key={comp}>
                    <td><code>{comp}</code></td>
                    <td>{count} issue{count !== 1 ? 's' : ''}</td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      )}

      {activeTab === 'categories' && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Category</th>
              <th>Count</th>
            </tr>
          </thead>
          <tbody>
            {Object.keys(categories).length === 0 ? (
              <tr>
                <td colSpan={2} style={{ textAlign: 'center', color: '#6b7280' }}>
                  No issues found
                </td>
              </tr>
            ) : (
              Object.entries(categories)
                .sort(([, a], [, b]) => b - a)
                .map(([cat, count]) => (
                  <tr key={cat}>
                    <td>
                      <span className="attr-badge">{cat.toUpperCase()}</span>
                    </td>
                    <td><strong>{count}</strong></td>
                  </tr>
                ))
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}
