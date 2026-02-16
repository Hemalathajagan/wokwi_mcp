import { useState } from 'react';

export default function UrlInput({ onAnalyze, loading }) {
  const [url, setUrl] = useState('');
  const [description, setDescription] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (url.trim()) {
      onAnalyze({ url: url.trim(), description: description.trim() });
    }
  };

  return (
    <form onSubmit={handleSubmit} className="url-input">
      <div className="input-group">
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://wokwi.com/projects/..."
          disabled={loading}
          required
        />
        <button type="submit" disabled={loading || !url.trim()}>
          {loading ? (
            <>
              <span className="spinner"></span>
              Analyzing...
            </>
          ) : (
            'Analyze Circuit'
          )}
        </button>
      </div>
      <p className="hint">Paste a public Wokwi project URL to analyze it for circuit and code faults</p>

      <div className="design-description">
        <label htmlFor="wokwi-description">
          Design Description (optional — helps detect functional wiring mistakes)
        </label>
        <textarea
          id="wokwi-description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Describe what your circuit should do, including specific pin assignments..."
          disabled={loading}
          rows={3}
        />
        <p className="description-examples">
          Tip: Describe your circuit's purpose and pin connections. Examples:<br />
          &bull; "ESP32 reads DHT22 sensor on GPIO4, controls relay on GPIO5, OLED on I2C (SDA=21, SCL=22)"<br />
          &bull; "Arduino Uno with 3 LEDs on pins 9-11, push button on pin 2, buzzer on pin 8"<br />
          &bull; "STM32F103 driving stepper motor via A4988: STEP=PA0, DIR=PA1, EN=PA2"
        </p>
      </div>
    </form>
  );
}
