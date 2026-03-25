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
// AUTH DISABLED -- uncomment below to re-enable login/signup
// import LoginPage from './auth/LoginPage';
// import ProtectedRoute from './auth/ProtectedRoute';
// import UserMenu from './auth/UserMenu';
// import ProfilePage from './pages/ProfilePage';
// import HistoryPage from './pages/HistoryPage';
// import HistoryDetailPage from './pages/HistoryDetailPage';
import './App.css';

function Dashboard() {
  const [mode, setMode] = useState('wokwi');
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [status, setStatus] = useState(null); // transient info messages (warm-up)
  const [activeSection, setActiveSection] = useState('faults');

  const runWithWarmup = async (apiFn, projectType) => {
    const MAX_RETRIES = 3;
    const RETRY_DELAY_MS = 20000;
    for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
      try {
        const result = await apiFn();
        setStatus(null);
        return result;
      } catch (err) {
        if (err.response) throw err; // real API error — don't retry
        if (attempt < MAX_RETRIES) {
          setStatus(`Server is starting up on Render… retrying (${attempt}/${MAX_RETRIES - 1}). Please wait.`);
          await new Promise(r => setTimeout(r, RETRY_DELAY_MS));
        } else {
          setStatus(null);
          throw new Error('Server is unavailable. Please try again in a moment.');
        }
      }
    }
  };

  const handleAnalyze = async ({ url, description }) => {
    setLoading(true);
    setError(null);
    setStatus(null);
    setReport(null);
    setActiveSection('faults');
    try {
      const result = await runWithWarmup(() => analyzeProject(url, description), 'wokwi');
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
    setStatus(null);
    setReport(null);
    setActiveSection('faults');
    try {
      const result = await runWithWarmup(() => uploadKiCadFiles(files, description), 'kicad');
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
      setStatus(null);
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

      {status && (
        <div className="status-banner">
          <span className="spinner" />
          {status}
        </div>
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
          {/* AUTH DISABLED -- <UserMenu /> */}
        </div>
      </header>

      <main>
        {/* AUTH DISABLED -- routes open without login */}
        <Routes>
          <Route path="/" element={<Dashboard />} />
        </Routes>

        {/* ORIGINAL (with auth) -- uncomment to re-enable login/signup:
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
          <Route path="/history" element={<ProtectedRoute><HistoryPage /></ProtectedRoute>} />
          <Route path="/history/:id" element={<ProtectedRoute><HistoryDetailPage /></ProtectedRoute>} />
        </Routes>
        */}
      </main>

      <footer>
        <p>Powered by OpenAI GPT-4o | Analyzes Wokwi and KiCad projects</p>
      </footer>
    </div>
  );
}

export default App;
