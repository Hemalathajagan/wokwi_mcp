export default function SummaryBar({ summary }) {
  if (!summary) return null;

  return (
    <div className="summary-bar">
      <div className="summary-item total">
        <span className="count">{summary.total_faults}</span>
        <span className="label">Total Issues</span>
      </div>
      <div className="summary-item errors">
        <span className="count">{summary.errors}</span>
        <span className="label">Errors</span>
      </div>
      <div className="summary-item warnings">
        <span className="count">{summary.warnings}</span>
        <span className="label">Warnings</span>
      </div>
      <div className="summary-item infos">
        <span className="count">{summary.infos}</span>
        <span className="label">Info</span>
      </div>
    </div>
  );
}
