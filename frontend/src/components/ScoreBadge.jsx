/**
 * ScoreBadge — small metric tile with animated progress arc.
 */
export default function ScoreBadge({ label, value = 0, subText = '', accent = 'var(--cyan)' }) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100)
  const color = pct >= 70 ? accent
              : pct >= 40 ? '#fbbf24'
              :             '#fb7185'
  return (
    <div className="score-badge">
      <span className="sb-label">{label}</span>
      <span className="sb-value" style={{ color }}>{pct}<span style={{ fontSize: '0.85rem', fontWeight: 600 }}>%</span></span>
      {subText && <span className="sb-sub">{subText}</span>}
      <div style={{ width: '100%', marginTop: '0.4rem' }}>
        <div className="progress-bar">
          <div className="progress-bar-fill" style={{
            width: `${pct}%`,
            background: `linear-gradient(90deg, ${color}99, ${color})`,
          }} />
        </div>
      </div>
    </div>
  )
}
