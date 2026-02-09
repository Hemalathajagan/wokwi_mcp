export default function CodeView({ sketchCode, faults }) {
  if (!sketchCode) return null;

  // Find lines with issues
  const problemLines = new Map();
  if (faults) {
    faults.forEach((fault) => {
      if (fault.category === 'code' || fault.category === 'cross_reference') {
        // Try to extract line numbers from the fix description or title
        const lineMatch = fault.title?.match(/line\s+(\d+)/i)
          || fault.explanation?.match(/line\s+(\d+)/i);
        if (lineMatch) {
          const lineNum = parseInt(lineMatch[1]);
          problemLines.set(lineNum, fault);
        }
      }
    });
  }

  const lines = sketchCode.split('\n');

  return (
    <div className="code-view">
      <h2>Arduino Sketch</h2>
      <div className="code-container">
        <pre>
          {lines.map((line, i) => {
            const lineNum = i + 1;
            const fault = problemLines.get(lineNum);
            const className = fault
              ? fault.severity === 'error'
                ? 'line-error'
                : 'line-warning'
              : '';

            return (
              <div key={lineNum} className={`code-line ${className}`}>
                <span className="line-number">{lineNum}</span>
                <span className="line-content">{line}</span>
                {fault && (
                  <span className="line-annotation" title={fault.explanation}>
                    {fault.severity === 'error' ? '\u274C' : '\u26A0\uFE0F'} {fault.title}
                  </span>
                )}
              </div>
            );
          })}
        </pre>
      </div>
    </div>
  );
}
