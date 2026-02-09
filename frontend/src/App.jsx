import { useState } from 'react';
import { Routes, Route } from 'react-router-dom';
import UrlInput from './components/UrlInput';
import SummaryBar from './components/SummaryBar';
import CircuitViewer from './components/CircuitViewer';
import FaultReport from './components/FaultReport';
import CodeView from './components/CodeView';
import FixSuggestion from './components/FixSuggestion';
import { analyzeProject } from './api';
import LoginPage from './auth/LoginPage';
import ProtectedRoute from './auth/ProtectedRoute';
import UserMenu from './auth/UserMenu';
import ProfilePage from './pages/ProfilePage';
import HistoryPage from './pages/HistoryPage';
import HistoryDetailPage from './pages/HistoryDetailPage';
import './App.css';

function Dashboard() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeSection, setActiveSection] = useState('faults');

  const handleAnalyze = async (url) => {
    setLoading(true);
    setError(null);
    setReport(null);
    try {
      const result = await analyzeProject(url);
      setReport(result);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <UrlInput onAnalyze={handleAnalyze} loading={loading} />

      {error && (
        <div className="error-banner">
          <strong>Error:</strong> {error}
        </div>
      )}

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
            {activeSection === 'faults' && (
              <FaultReport faults={report.faults} />
            )}
            {activeSection === 'circuit' && (
              <CircuitViewer diagram={report.diagram} />
            )}
            {activeSection === 'code' && (
              <CodeView
                sketchCode={report.sketch_code}
                faults={report.faults}
              />
            )}
            {activeSection === 'fix' && (
              <FixSuggestion report={report} />
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
            <h1>Wokwi Circuit Analyzer</h1>
            <p className="subtitle">AI-powered Arduino circuit fault detection</p>
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
        <p>Powered by OpenAI GPT-4o | Analyzes public Wokwi projects</p>
      </footer>
    </div>
  );
}

export default App;
