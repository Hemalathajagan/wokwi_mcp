import { useState } from 'react';

export default function CircuitViewer({ diagram }) {
  const [activeTab, setActiveTab] = useState('parts');

  if (!diagram || !diagram.parts) return null;

  const parts = diagram.parts || [];
  const connections = diagram.connections || [];

  return (
    <div className="circuit-viewer">
      <h2>Circuit Overview</h2>
      <div className="tabs">
        <button
          className={activeTab === 'parts' ? 'active' : ''}
          onClick={() => setActiveTab('parts')}
        >
          Components ({parts.length})
        </button>
        <button
          className={activeTab === 'connections' ? 'active' : ''}
          onClick={() => setActiveTab('connections')}
        >
          Connections ({connections.length})
        </button>
      </div>

      {activeTab === 'parts' && (
        <table className="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Type</th>
              <th>Attributes</th>
            </tr>
          </thead>
          <tbody>
            {parts.map((part) => (
              <tr key={part.id}>
                <td><code>{part.id}</code></td>
                <td>{part.type.replace('wokwi-', '')}</td>
                <td>
                  {part.attrs
                    ? Object.entries(part.attrs).map(([k, v]) => (
                        <span key={k} className="attr-badge">
                          {k}: {v}
                        </span>
                      ))
                    : '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {activeTab === 'connections' && (
        <table className="data-table">
          <thead>
            <tr>
              <th>From</th>
              <th>To</th>
              <th>Wire Color</th>
            </tr>
          </thead>
          <tbody>
            {connections.map((conn, i) => (
              <tr key={i}>
                <td><code>{conn[0]}</code></td>
                <td><code>{conn[1]}</code></td>
                <td>
                  {conn[2] ? (
                    <span className="wire-color" style={{
                      backgroundColor: conn[2],
                      color: ['white', 'yellow', 'lime'].includes(conn[2]) ? '#333' : '#fff'
                    }}>
                      {conn[2]}
                    </span>
                  ) : (
                    <span className="wire-hidden">hidden</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
