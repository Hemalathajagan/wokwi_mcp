import { useState } from 'react';
import { Routes, Route } from 'react-router-dom';
import UrlInput from './components/UrlInput';
import KiCadUpload from './components/KiCadUpload';
import SummaryBar from './components/SummaryBar';
import CircuitViewer from './components/CircuitViewer';
import SchematicViewer from './components/SchematicViewer';
import FaultReport from './components/FaultReport';
import CodeView from './components/CodeView';
import FixSuggestion from './components/FixSuggestion';
import { analyzeProject, uploadKiCadFiles } from './api';
import LoginPage from './auth/LoginPage';
import ProtectedRoute from './auth/ProtectedRoute';
import UserMenu from './auth/UserMenu';
import ProfilePage from './pages/ProfilePage';
import HistoryPage from './pages/HistoryPage';
import HistoryDetailPage from './pages/HistoryDetailPage';
import './App.css';

function Dashboard() {
  const [mode, setMode] = useState('wokwi');
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeSection, setActiveSection] = useState('faults');

  const handleAnalyze = async ({ url, description }) => {
    setLoading(true);
    setError(null);
    setReport(null);
    setActiveSection('faults');
    try {
      const result = await analyzeProject(url, description);
      setReport({ ...result, _projectType: 'wokwi' });
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleKiCadAnalyze = async ({ files, description }) => {
    setLoading(true);
    setError(null);
    setReport(null);
    setActiveSection('faults');
    try {
      const result = await uploadKiCadFiles(files, description);
      setReport({ ...result, _projectType: 'kicad' });
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleModeSwitch = (newMode) => {
    if (newMode !== mode) {
      setMode(newMode);
      setReport(null);
      setError(null);
      setActiveSection('faults');
    }
  };

  const projectType = report?._projectType || mode;
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
    <>
      <div className="mode-toggle">
        <button
          className={mode === 'wokwi' ? 'active' : ''}
          onClick={() => handleModeSwitch('wokwi')}
        >
          Wokwi
        </button>
        <button
          className={mode === 'kicad' ? 'active' : ''}
          onClick={() => handleModeSwitch('kicad')}
        >
          KiCad
        </button>
      </div>

      {mode === 'wokwi' ? (
        <UrlInput onAnalyze={handleAnalyze} loading={loading} />
      ) : (
        <KiCadUpload onAnalyze={handleKiCadAnalyze} loading={loading} />
      )}

      {error && (
        <div className="error-banner">
          <strong>Error:</strong> {error}
        </div>
      )}

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
            {activeSection === 'faults' && (
              <FaultReport faults={report.faults} />
            )}
            {activeSection === 'circuit' && !isKiCad && (
              <CircuitViewer diagram={report.diagram} />
            )}
            {activeSection === 'schematic' && isKiCad && (
              <SchematicViewer report={report} />
            )}
            {activeSection === 'code' && !isKiCad && (
              <CodeView
                sketchCode={report.sketch_code}
                faults={report.faults}
              />
            )}
            {activeSection === 'fix' && (
              <FixSuggestion report={report} projectType={projectType} />
            )}
          </div>
        </>
      )}
    </>
  );
}

function App() {
  return (
    <div className="app">
      <header>
        <div className="header-row">
          <div>
            <h1>Circuit Analyzer</h1>
            <p className="subtitle">AI-powered circuit fault detection for Wokwi & KiCad</p>
          </div>
          <UserMenu />
        </div>
      </header>

      <main>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/profile"
            element={
              <ProtectedRoute>
                <ProfilePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/history"
            element={
              <ProtectedRoute>
                <HistoryPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/history/:id"
            element={
              <ProtectedRoute>
                <HistoryDetailPage />
              </ProtectedRoute>
            }
          />
        </Routes>
      </main>

      <footer>
        <p>Powered by OpenAI GPT-4o | Analyzes Wokwi and KiCad projects</p>
      </footer>
    </div>
  );
}

export default App;
