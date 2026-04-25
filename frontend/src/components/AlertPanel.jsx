/**
 * AlertPanel — displays a color-coded, scrollable list of alerts.
 * Severity: CRITICAL (red), HIGH (orange), MEDIUM (yellow), LOW (blue)
 */
const SEVERITY_ICONS = {
  CRITICAL: '🔴',
  HIGH:     '🟠',
  MEDIUM:   '🟡',
  LOW:      '🔵',
}

const ALERT_LABELS = {
  FACE_ABSENT:        'Face Not Visible',
  MULTIPLE_FACES:     'Multiple Faces',
  SPOOF_DETECTED:     'Spoofing Detected',
  HEAD_TURNED:        'Head Turned Away',
  GAZE_AWAY:          'Gaze Off Screen',
  LOW_ATTENTION:      'Low Attention',
  LIP_MOVEMENT:       'Lip Movement',
  EXCESSIVE_MOVEMENT: 'Excessive Movement',
  LOOKING_DOWN:       'Looking Down',
  BLINK_ABSENT:       'No Blink Detected',
}

function AlertItem({ alert }) {
  const sev = (alert.severity || 'MEDIUM').toLowerCase()
  const icon = SEVERITY_ICONS[alert.severity] || '⚪'
  const label = ALERT_LABELS[alert.type] || alert.type?.replace(/_/g, ' ')
  const time = alert.timestamp
    ? new Date(alert.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    : ''

  return (
    <div className={`alert-item alert-${sev}`}>
      <span style={{ fontSize: '1rem', flexShrink: 0, lineHeight: 1 }}>{icon}</span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 600, fontSize: '0.82rem' }}>{label}</div>
        {alert.details && Object.keys(alert.details).length > 0 && (
          <div style={{ fontSize: '0.74rem', opacity: 0.75, marginTop: '0.15rem', fontFamily: 'var(--font-mono)' }}>
            {Object.entries(alert.details)
              .map(([k, v]) => `${k}: ${typeof v === 'number' ? v.toFixed(2) : v}`)
              .join(' · ')}
          </div>
        )}
      </div>
      <span style={{ fontSize: '0.7rem', opacity: 0.6, flexShrink: 0, fontFamily: 'var(--font-mono)' }}>{time}</span>
    </div>
  )
}

export default function AlertPanel({ alerts = [], maxHeight = 280 }) {
  const sorted = [...alerts].reverse() // newest first

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <span className="section-title">Live Alerts</span>
        {alerts.length > 0 && (
          <span style={{
            background: 'var(--rose-dim)', color: 'var(--rose)',
            borderRadius: '999px', padding: '0.15rem 0.55rem',
            fontSize: '0.72rem', fontWeight: 700,
            border: '1px solid rgba(251,113,133,0.25)',
          }}>
            {alerts.length}
          </span>
        )}
      </div>

      <div style={{ maxHeight, overflowY: 'auto', paddingRight: '2px' }}>
        {sorted.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2rem 1rem' }}>
            <div style={{ fontSize: '1.8rem', marginBottom: '0.5rem' }}>✅</div>
            <p style={{ fontSize: '0.83rem' }}>No alerts recorded</p>
          </div>
        ) : (
          sorted.map(a => <AlertItem key={a.id || Math.random()} alert={a} />)
        )}
      </div>
    </div>
  )
}
