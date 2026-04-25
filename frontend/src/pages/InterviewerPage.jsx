import { useEffect, useState, useCallback, useRef } from 'react'
import AlertPanel    from '../components/AlertPanel.jsx'
import ScoreBadge    from '../components/ScoreBadge.jsx'
import TrustGauge    from '../components/TrustGauge.jsx'
import BehaviorBars  from '../components/BehaviorBars.jsx'

const RISK_COLOR = (r) =>
  r < 5  ? 'var(--emerald)' :
  r < 20 ? 'var(--amber)'   :
           'var(--rose)'

const RECOMMENDATION_STYLE = {
  PASS:   { bg: 'var(--emerald-dim)', color: 'var(--emerald)', border: 'rgba(52,211,153,0.3)',  icon: '✓' },
  REVIEW: { bg: 'var(--amber-dim)',   color: 'var(--amber)',   border: 'rgba(251,191,36,0.3)',  icon: '⚠' },
  FAIL:   { bg: 'var(--rose-dim)',    color: 'var(--rose)',    border: 'rgba(251,113,133,0.3)', icon: '✗' },
}

function GazeBar({ label, pct, color }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.4rem' }}>
      <span style={{ width: 52, fontSize: '0.75rem', color: 'var(--text-secondary)', textAlign: 'right', flexShrink: 0 }}>{label}</span>
      <div style={{ flex: 1, height: 8, borderRadius: 4, background: 'rgba(255,255,255,0.05)', overflow: 'hidden' }}>
        <div style={{
          height: '100%', borderRadius: 4, width: `${pct}%`,
          background: `linear-gradient(90deg, ${color}99, ${color})`,
          transition: 'width 0.5s ease',
        }} />
      </div>
      <span className="mono" style={{ width: 38, fontSize: '0.75rem', color, textAlign: 'right', flexShrink: 0 }}>{pct?.toFixed(1)}%</span>
    </div>
  )
}

function SessionCard({ session, onSelect, isSelected }) {
  const risk = session.risk_score ?? 0
  const trust = session.avg_trust_score ?? 0
  const initial = (session.candidate_name || '?')[0].toUpperCase()
  const rColor = RISK_COLOR(risk)
  return (
    <div
      className="card"
      style={{
        cursor: 'pointer',
        borderColor: isSelected ? 'var(--border-bright)' : undefined,
        transition: 'all 0.15s',
        background: isSelected ? 'var(--bg-card-2)' : undefined,
      }}
      onClick={() => onSelect(session)}
    >
      <div className="flex items-center gap-3 mb-2">
        <div style={{
          width: 38, height: 38, borderRadius: '50%',
          background: 'linear-gradient(135deg, var(--cyan), var(--violet))',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontWeight: 800, fontSize: '0.95rem', color: '#fff', flexShrink: 0,
        }}>{initial}</div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 600, fontSize: '0.92rem', truncate: true }}>{session.candidate_name}</div>
          <span className={`pill ${session.status === 'active' ? 'live' : 'unknown'}`} style={{ fontSize: '0.7rem' }}>
            {session.status === 'active' ? '🟢 Live' : '⚫ Closed'}
          </span>
        </div>
      </div>
      <div className="mono" style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginBottom: '0.6rem' }}>
        {session.session_id?.substring(0, 18)}…
      </div>
      {/* Mini metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.3rem', marginBottom: '0.6rem' }}>
        {[
          ['Trust', `${Math.round(trust * 100)}%`, trust > 0.65 ? 'var(--emerald)' : trust > 0.35 ? 'var(--amber)' : 'var(--rose)'],
          ['Risk',  risk.toFixed(1), rColor],
        ].map(([k, v, c]) => (
          <div key={k} style={{ background: 'var(--bg-card-2)', borderRadius: 6, padding: '0.3rem 0.5rem', textAlign: 'center' }}>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{k}</div>
            <div className="mono" style={{ fontSize: '0.9rem', fontWeight: 700, color: c }}>{v}</div>
          </div>
        ))}
      </div>
      <div className="progress-bar">
        <div className="progress-bar-fill" style={{ width: `${Math.min(risk * 2, 100)}%`, background: rColor }} />
      </div>
    </div>
  )
}

export default function InterviewerPage() {
  const [sessions, setSessions]   = useState([])
  const [selected, setSelected]   = useState(null)
  const [report, setReport]       = useState(null)
  const [loading, setLoading]     = useState(false)
  const [activeTab, setActiveTab] = useState('metrics') // 'metrics' | 'alerts' | 'gaze'
  const pollRef = useRef(null)

  const loadSessions = useCallback(async () => {
    try {
      const res = await fetch('/sessions')
      if (res.ok) {
        const data = await res.json()
        setSessions(data)
        // Auto-refresh selected session's data if it's active
        if (selected) {
          const updated = data.find(s => s.session_id === selected.session_id)
          if (updated) setSelected(updated)
        }
      }
    } catch {}
  }, [selected])

  const loadReport = useCallback(async (sid) => {
    setLoading(true)
    try {
      const res = await fetch(`/report/${sid}`)
      if (res.ok) setReport(await res.json())
    } catch {}
    setLoading(false)
  }, [])

  useEffect(() => {
    loadSessions()
    pollRef.current = setInterval(loadSessions, 3000)
    return () => clearInterval(pollRef.current)
  }, [loadSessions])

  function handleSelect(session) {
    setSelected(session)
    setReport(null)
    loadReport(session.session_id)
    setActiveTab('metrics')
  }

  function downloadReport() {
    if (!report) return
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href = url
    a.download = `report_${report.session_id?.substring(0, 8)}_${report.candidate_name}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const recStyle = report ? RECOMMENDATION_STYLE[report.recommendation] || RECOMMENDATION_STYLE.REVIEW : null

  return (
    <main className="page">
      {/* ── Header ──────────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-4" style={{ flexWrap: 'wrap', gap: '0.75rem' }}>
        <div>
          <h2>Interviewer Dashboard</h2>
          <p style={{ fontSize: '0.85rem', marginTop: '0.2rem' }}>
            Monitor all candidate sessions · auto-refreshes every 3s
          </p>
        </div>
        <button id="refresh-sessions-btn" className="btn btn-secondary" onClick={loadSessions}>
          🔄 Refresh
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: '1.5rem', alignItems: 'start' }}>
        {/* ── Session list ─────────────────────────────────── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
          <div className="flex items-center justify-between mb-1">
            <span className="section-title">Sessions</span>
            <span style={{
              background: 'var(--cyan-dim)', color: 'var(--cyan)',
              borderRadius: '999px', padding: '0.12rem 0.5rem',
              fontSize: '0.72rem', fontWeight: 700,
            }}>{sessions.length}</span>
          </div>

          {sessions.length === 0 ? (
            <div className="card" style={{ textAlign: 'center', padding: '2.5rem 1rem' }}>
              <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>📋</div>
              <p style={{ fontSize: '0.83rem' }}>No sessions yet.<br />Start a candidate session first.</p>
            </div>
          ) : (
            sessions.map(s => (
              <SessionCard
                key={s.session_id}
                session={s}
                onSelect={handleSelect}
                isSelected={selected?.session_id === s.session_id}
              />
            ))
          )}
        </div>

        {/* ── Detail panel ─────────────────────────────────── */}
        <div>
          {!selected ? (
            <div className="card" style={{ textAlign: 'center', padding: '5rem 2rem' }}>
              <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>👈</div>
              <h3 style={{ marginBottom: '0.5rem' }}>Select a session</h3>
              <p>Choose a candidate from the left to view their live analysis.</p>
            </div>
          ) : loading ? (
            <div className="card" style={{ display: 'flex', justifyContent: 'center', padding: '5rem' }}>
              <div className="spinner" style={{ width: 36, height: 36 }} />
            </div>
          ) : report ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {/* ── Top bar ───────────────────────────────────── */}
              <div className="card" style={{ padding: '1.25rem' }}>
                <div className="flex items-center justify-between flex-wrap gap-3">
                  <div>
                    <h3 style={{ marginBottom: '0.2rem' }}>{report.candidate_name}</h3>
                    <p style={{ fontSize: '0.8rem' }}>
                      Duration: {Math.round(report.duration_seconds)}s ·
                      Frames: {report.total_frames_processed} ·
                      Alerts: {report.total_alerts} ·
                      Rate: {report.alert_rate_per_min?.toFixed(2)}/min
                    </p>
                  </div>
                  <div className="flex gap-2 items-center">
                    {recStyle && (
                      <div style={{
                        padding: '0.4rem 1.1rem', borderRadius: '999px', fontWeight: 700, fontSize: '0.85rem',
                        background: recStyle.bg, color: recStyle.color,
                        border: `1px solid ${recStyle.border}`,
                      }}>
                        {recStyle.icon} {report.recommendation}
                      </div>
                    )}
                    <button id="download-report-btn" className="btn btn-violet" onClick={downloadReport}>
                      ⬇ Download
                    </button>
                  </div>
                </div>
              </div>

              {/* ── Trust gauge + risk ────────────────────────── */}
              <div className="card">
                <div className="flex items-center gap-4 flex-wrap">
                  <TrustGauge
                    value={report.metrics?.avg_trust_score ?? 0}
                    label="Trust Score"
                    size={150}
                  />
                  <div style={{ flex: 1, minWidth: 200 }}>
                    <div className="section-title mb-1">Risk Score</div>
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.4rem', marginBottom: '0.5rem' }}>
                      <span className="mono" style={{
                        fontSize: '2.2rem', fontWeight: 800,
                        color: RISK_COLOR(report.risk_score),
                      }}>{report.risk_score?.toFixed(1)}</span>
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>/ 100</span>
                    </div>
                    <div className="progress-bar" style={{ height: 10 }}>
                      <div className="progress-bar-fill" style={{
                        width: `${Math.min(report.risk_score, 100)}%`,
                        background: RISK_COLOR(report.risk_score),
                        boxShadow: `0 0 8px ${RISK_COLOR(report.risk_score)}60`,
                      }} />
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.4rem' }}>
                      Low &lt;5 · Review 5–20 · Fail &gt;20
                    </div>
                  </div>
                </div>
              </div>

              {/* ── Tab navigation ────────────────────────────── */}
              <div className="flex gap-2">
                {['metrics', 'alerts', 'gaze'].map(tab => (
                  <button
                    key={tab}
                    className={`btn ${activeTab === tab ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ fontSize: '0.8rem', textTransform: 'capitalize' }}
                    onClick={() => setActiveTab(tab)}
                  >
                    {tab === 'metrics' ? '📊 Metrics' : tab === 'alerts' ? '🚨 Alerts' : '👁 Gaze'}
                  </button>
                ))}
              </div>

              {/* ── Metrics tab ───────────────────────────────── */}
              {activeTab === 'metrics' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  {/* Score badges */}
                  <div className="card">
                    <div className="section-title mb-3">Session Scores</div>
                    <div className="grid-4" style={{ gap: '0.75rem' }}>
                      <ScoreBadge label="Attention"    value={report.metrics?.avg_attention_score ?? 0} accent="var(--cyan)" />
                      <ScoreBadge label="Liveness"     value={report.metrics?.avg_liveness_score  ?? 0} accent="var(--emerald)" />
                      <ScoreBadge label="Eye Contact"  value={report.metrics?.avg_eye_contact     ?? 0} accent="var(--violet)" />
                      <ScoreBadge label="Authenticity" value={report.metrics?.avg_spoof_confidence ?? 0} accent="var(--amber)" />
                    </div>
                  </div>

                  {/* Percentage breakdown */}
                  <div className="card">
                    <div className="section-title mb-3">Behavioral Percentages</div>
                    <BehaviorBars data={{
                      attention:   (report.metrics?.avg_attention_score ?? 0),
                      liveness:    (report.metrics?.avg_liveness_score  ?? 0),
                      eye_contact: (report.metrics?.avg_eye_contact     ?? 0),
                      spoof_clean: (report.metrics?.avg_spoof_confidence ?? 0),
                    }} />
                    <div style={{ marginTop: '1rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border)' }}>
                      <div className="flex justify-between" style={{ fontSize: '0.82rem' }}>
                        <span style={{ color: 'var(--text-secondary)' }}>Overall Integrity Score</span>
                        <span className="mono" style={{
                          fontWeight: 700,
                          color: (report.percentages?.integrity ?? 0) >= 70 ? 'var(--emerald)' :
                                 (report.percentages?.integrity ?? 0) >= 40 ? 'var(--amber)' : 'var(--rose)',
                        }}>
                          {report.percentages?.integrity?.toFixed(1) ?? '--'}%
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Event counts */}
                  <div className="card">
                    <div className="section-title mb-3">Event Counts</div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: '0.5rem' }}>
                      {[
                        ['Spoof Events',    report.metrics?.spoof_events,         'var(--rose)'],
                        ['Lip Movements',   report.metrics?.lip_movement_events,  'var(--amber)'],
                        ['Body Movements',  report.metrics?.body_movement_events, 'var(--amber)'],
                        ['Head Turns',      report.metrics?.head_turn_events,     'var(--violet)'],
                        ['Gaze Away',       report.metrics?.gaze_away_events,     'var(--cyan)'],
                        ['Total Alerts',    report.total_alerts,                  'var(--rose)'],
                      ].map(([label, val, color]) => (
                        <div key={label} style={{
                          background: 'var(--bg-card-2)', borderRadius: 8, padding: '0.6rem 0.75rem', textAlign: 'center',
                        }}>
                          <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.2rem' }}>{label}</div>
                          <div className="mono" style={{ fontSize: '1.2rem', fontWeight: 800, color: (val ?? 0) > 0 ? color : 'var(--emerald)' }}>
                            {val ?? 0}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* ── Alerts tab ────────────────────────────────── */}
              {activeTab === 'alerts' && (
                <div className="grid-2" style={{ alignItems: 'start' }}>
                  <div className="card">
                    <AlertPanel alerts={report.alerts ?? []} maxHeight={400} />
                  </div>
                  <div className="card">
                    <div className="section-title mb-3">Alert Summary</div>
                    {Object.keys(report.alert_summary ?? {}).length === 0 ? (
                      <p style={{ textAlign: 'center', padding: '2rem', fontSize: '0.85rem' }}>✅ No alerts recorded</p>
                    ) : (
                      Object.entries(report.alert_summary)
                        .sort(([,a],[,b]) => b - a)
                        .map(([type, count]) => (
                          <div key={type} style={{
                            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                            padding: '0.5rem 0.75rem', background: 'var(--bg-card-2)',
                            borderRadius: 6, marginBottom: '0.4rem', fontSize: '0.83rem',
                          }}>
                            <span style={{ color: 'var(--text-secondary)' }}>{type.replace(/_/g, ' ')}</span>
                            <div className="flex items-center gap-2">
                              <span className="mono" style={{ fontWeight: 700, color: 'var(--amber)' }}>×{count}</span>
                              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                                {report.alert_rates?.[type]?.toFixed(2)}/min
                              </span>
                            </div>
                          </div>
                        ))
                    )}
                  </div>
                </div>
              )}

              {/* ── Gaze tab ──────────────────────────────────── */}
              {activeTab === 'gaze' && (
                <div className="card">
                  <div className="section-title mb-4">Gaze Distribution</div>
                  <div style={{ maxWidth: 420 }}>
                    {[
                      ['CENTER', report.gaze_distribution?.center ?? 0, '#34d399'],
                      ['LEFT',   report.gaze_distribution?.left   ?? 0, '#fbbf24'],
                      ['RIGHT',  report.gaze_distribution?.right  ?? 0, '#fbbf24'],
                      ['DOWN',   report.gaze_distribution?.down   ?? 0, '#fb7185'],
                      ['UP',     report.gaze_distribution?.up     ?? 0, '#a78bfa'],
                    ].map(([label, pct, color]) => (
                      <GazeBar key={label} label={label} pct={pct} color={color} />
                    ))}
                  </div>
                  <div style={{
                    marginTop: '1.25rem', paddingTop: '1rem', borderTop: '1px solid var(--border)',
                    fontSize: '0.82rem', color: 'var(--text-secondary)',
                  }}>
                    <strong style={{ color: 'var(--text-primary)' }}>Interpretation: </strong>
                    CENTER &gt;60% = excellent engagement ·
                    &lt;40% = concerning ·
                    HIGH DOWN suggests phone/notes reference
                  </div>
                </div>
              )}
            </div>
          ) : null}
        </div>
      </div>
    </main>
  )
}
