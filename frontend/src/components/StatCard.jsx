export default function StatCard({ label, value, unit, note }) {
  return <article className="stat-card"><p className="stat-label">{label}</p><div className="stat-value">{value}<span>{unit}</span></div>{note && <p className="stat-note">{note}</p>}</article>;
}
