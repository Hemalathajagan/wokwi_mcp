import { useState, useRef } from 'react';

const ALLOWED_EXTENSIONS = ['.kicad_sch', '.kicad_pcb', '.kicad_pro'];

function isAllowed(filename) {
  return ALLOWED_EXTENSIONS.some((ext) => filename.toLowerCase().endsWith(ext));
}

export default function KiCadUpload({ onAnalyze, loading }) {
  const [files, setFiles] = useState([]);
  const [dragOver, setDragOver] = useState(false);
  const [description, setDescription] = useState('');
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
      onAnalyze({ files, description: description.trim() });
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

      <div className="design-description">
        <label htmlFor="kicad-description">
          Design Description (optional — helps detect functional wiring mistakes)
        </label>
        <textarea
          id="kicad-description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Describe what your circuit should do, including specific pin assignments..."
          disabled={loading}
          rows={3}
        />
        <p className="description-examples">
          Tip: Describe your circuit's purpose and pin connections. Examples:<br />
          &bull; "ESP32 reads DHT22 sensor on GPIO4, controls relay on GPIO5, OLED on I2C (SDA=21, SCL=22)"<br />
          &bull; "ATmega328P with 16MHz crystal, 3 LEDs on PB0-PB2, UART to GPS module on PD0/PD1"<br />
          &bull; "STM32F103 driving stepper motor via A4988: STEP=PA0, DIR=PA1, EN=PA2"
        </p>
      </div>
    </form>
  );
}
