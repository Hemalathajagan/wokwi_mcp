import { useState, useRef } from 'react';

const ALLOWED_EXTENSIONS = ['.kicad_sch', '.kicad_pcb', '.kicad_pro'];

function isAllowed(filename) {
  return ALLOWED_EXTENSIONS.some((ext) => filename.toLowerCase().endsWith(ext));
}

export default function KiCadUpload({ onAnalyze, loading }) {
  const [files, setFiles] = useState([]);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef(null);

  const addFiles = (fileList) => {
    const newFiles = Array.from(fileList).filter(
      (f) => isAllowed(f.name) && !files.some((existing) => existing.name === f.name)
    );
    if (newFiles.length > 0) {
      setFiles((prev) => [...prev, ...newFiles]);
    }
  };

  const removeFile = (name) => {
    setFiles((prev) => prev.filter((f) => f.name !== name));
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    addFiles(e.dataTransfer.files);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (files.length > 0) {
      onAnalyze(files);
    }
  };

  const hasSchOrPcb = files.some(
    (f) => f.name.endsWith('.kicad_sch') || f.name.endsWith('.kicad_pcb')
  );

  return (
    <form onSubmit={handleSubmit} className="kicad-upload">
      <div
        className={`drop-zone ${dragOver ? 'drag-over' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".kicad_sch,.kicad_pcb,.kicad_pro"
          style={{ display: 'none' }}
          onChange={(e) => { addFiles(e.target.files); e.target.value = ''; }}
        />
        <p className="drop-zone-text">
          {files.length === 0
            ? 'Drop KiCad files here or click to browse'
            : 'Drop more files or click to add'}
        </p>
        <p className="drop-zone-hint">.kicad_sch, .kicad_pcb, .kicad_pro</p>
      </div>

      {files.length > 0 && (
        <div className="file-list">
          {files.map((f) => (
            <span key={f.name} className="file-chip">
              {f.name}
              <button
                type="button"
                className="file-chip-remove"
                onClick={(e) => { e.stopPropagation(); removeFile(f.name); }}
              >
                x
              </button>
            </span>
          ))}
        </div>
      )}

      <div className="input-group" style={{ marginTop: '0.75rem' }}>
        <button type="submit" disabled={loading || !hasSchOrPcb}>
          {loading ? (
            <>
              <span className="spinner"></span>
              Analyzing...
            </>
          ) : (
            'Analyze KiCad Project'
          )}
        </button>
      </div>
      <p className="hint">Upload at least one .kicad_sch or .kicad_pcb file to analyze</p>
    </form>
  );
}
