/**
 * BehaviorBars — horizontal animated progress bars for each behavioral metric.
 */

const METRICS = [
  { key: 'attention',    label: 'Attention',    color: '#38bdf8' },
  { key: 'liveness',     label: 'Liveness',     color: '#34d399' },
  { key: 'eye_contact',  label: 'Eye Contact',  color: '#a78bfa' },
  { key: 'spoof_clean',  label: 'Authenticity', color: '#fbbf24' },
]

function barColor(pct, defaultColor) {
  if (pct >= 70) return defaultColor
  if (pct >= 40) return '#fbbf24'
  return '#fb7185'
}

export default function BehaviorBars({ data = {} }) {
  // data: { attention: 0-1, liveness: 0-1, eye_contact: 0-1, spoof_clean: 0-1 }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0' }}>
      {METRICS.map(({ key, label, color }) => {
        const raw = data[key] ?? 0
        const pct = Math.round(raw * 100)
        const c   = barColor(pct, color)
        return (
          <div key={key} className="behavior-bar-row">
            <div className="behavior-bar-label">
              <span style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>{label}</span>
              <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: c, fontSize: '0.85rem' }}>
                {pct}%
              </span>
            </div>
            <div className="behavior-bar-track">
              <div
                className="behavior-bar-fill"
                style={{
                  width: `${pct}%`,
                  background: `linear-gradient(90deg, ${c}cc, ${c})`,
                  boxShadow: `0 0 6px ${c}60`,
                }}
              />
            </div>
          </div>
        )
      })}
    </div>
  )
}
