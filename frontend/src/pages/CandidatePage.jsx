import { useEffect, useRef, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import useWebcam     from '../hooks/useWebcam.js'
import useWebSocket  from '../hooks/useWebSocket.js'
import TrustGauge    from '../components/TrustGauge.jsx'
import BehaviorBars  from '../components/BehaviorBars.jsx'
import AlertPanel    from '../components/AlertPanel.jsx'
import ScoreBadge    from '../components/ScoreBadge.jsx'

const WS_URL = (sid) => `ws://localhost:8000/ws/${sid}`
const FPS    = 10   // 10 frames per second

const GAZE_COLORS = {
  CENTER: '#34d399', LEFT: '#fbbf24', RIGHT: '#fbbf24',
  UP: '#a78bfa', DOWN: '#fb7185', UNKNOWN: '#475569',
}

export default function CandidatePage() {
  const navigate  = useNavigate()
  const sessionId = sessionStorage.getItem('session_id')
  const candName  = sessionStorage.getItem('candidate_name') || 'Candidate'

  useEffect(() => { if (!sessionId) navigate('/') }, [sessionId, navigate])

  const { videoRef, canvasRef, startCamera, stopCamera, captureFrame, isReady, error: camErr } =
    useWebcam(640, 480)
  const { connect, disconnect, send, lastMessage, status } =
    useWebSocket(WS_URL(sessionId))

  const intervalRef = useRef(null)
  const overlayRef  = useRef(null)

  const [running, setRunning]   = useState(false)
  const [result, setResult]     = useState(null)
  const [alerts, setAlerts]     = useState([])
  const [frameCount, setFrameCount] = useState(0)

  // Process incoming WS messages
  useEffect(() => {
    if (!lastMessage || lastMessage.error) return
    setResult(lastMessage)
    setFrameCount(c => c + 1)
    if (lastMessage.alerts?.length) {
      setAlerts(prev => [...prev, ...lastMessage.alerts].slice(-200))
    }
    drawOverlay(lastMessage)
  }, [lastMessage])

  function drawOverlay(r) {
    const canvas = overlayRef.current
    if (!canvas || !videoRef.current) return
    const vw = videoRef.current.videoWidth  || 640
    const vh = videoRef.current.videoHeight || 480
    canvas.width  = vw
    canvas.height = vh
    const ctx = canvas.getContext('2d')
    ctx.clearRect(0, 0, vw, vh)

    // ── Face bounding box ──────────────────────────────────────
    if (r.face_bbox) {
      const { x, y, w, h } = r.face_bbox
      const spoofColor = r.spoof_label === 'SPOOF' ? '#fb7185'
                       : r.spoof_label === 'REAL'  ? '#34d399'
                       :                             '#fbbf24'
      ctx.strokeStyle = spoofColor
      ctx.lineWidth   = 2.5
      ctx.shadowColor = spoofColor
      ctx.shadowBlur  = 12

      // Corner bracket style
      const cr = Math.min(14, w * 0.15)
      const lw = 2.5
      ctx.beginPath()
      // Top-left
      ctx.moveTo(x + cr, y); ctx.lineTo(x, y); ctx.lineTo(x, y + cr)
      // Top-right
      ctx.moveTo(x + w - cr, y); ctx.lineTo(x + w, y); ctx.lineTo(x + w, y + cr)
      // Bottom-right
      ctx.moveTo(x + w, y + h - cr); ctx.lineTo(x + w, y + h); ctx.lineTo(x + w - cr, y + h)
      // Bottom-left
      ctx.moveTo(x + cr, y + h); ctx.lineTo(x, y + h); ctx.lineTo(x, y + h - cr)
      ctx.stroke()
      ctx.shadowBlur = 0

      // Label
      const spoofTypeLabel = r.spoof_type === 'ai_face' ? '⚠ AI FACE'
                           : r.spoof_type === 'screen_replay' ? '⚠ SCREEN'
                           : r.spoof_type === 'printed_photo' ? '⚠ PHOTO'
                           : r.spoof_type === 'no_face' ? '⚠ NO FACE'
                           : '⚠ SPOOF'
      const labelText = r.spoof_label === 'SPOOF' ? spoofTypeLabel
                      : r.is_live ? '✓ LIVE' : '● VERIFYING'
      ctx.fillStyle = spoofColor
      ctx.font = 'bold 12px Inter, sans-serif'
      ctx.fillText(labelText, x + 2, y - 8)
    }

    // ── Gaze direction indicator ───────────────────────────────
    if (r.gaze_direction && r.gaze_direction !== 'UNKNOWN') {
      const gazeColor = GAZE_COLORS[r.gaze_direction] || '#fff'
      const gazeEmoji = r.gaze_direction === 'CENTER' ? '👁 CENTER'
                      : r.gaze_direction === 'LEFT'   ? '◀ LEFT'
                      : r.gaze_direction === 'RIGHT'  ? '▶ RIGHT'
                      : r.gaze_direction === 'UP'     ? '▲ UP'
                      :                                 '▼ DOWN'
      ctx.fillStyle = gazeColor
      ctx.font = 'bold 11px Inter, sans-serif'
      ctx.fillText(gazeEmoji, 12, vh - 12)
    }

    // ── Attention bar (top-right) ──────────────────────────────
    const bW = 130, bH = 8, bx = vw - bW - 12, by = 14
    ctx.fillStyle = 'rgba(0,0,0,0.5)'
    ctx.fillRect(bx - 6, by - 16, bW + 12, bH + 22)
    ctx.fillStyle = 'rgba(255,255,255,0.06)'
    ctx.fillRect(bx, by, bW, bH)
    const att = r.attention_score || 0
    const attColor = att > 0.65 ? '#34d399' : att > 0.35 ? '#fbbf24' : '#fb7185'
    ctx.fillStyle = attColor
    ctx.fillRect(bx, by, att * bW, bH)
    ctx.fillStyle = '#fff'
    ctx.font = '10px JetBrains Mono, monospace'
    ctx.fillText(`ATT ${Math.round(att * 100)}%`, bx, by - 4)

    // ── Trust score (top-left) ─────────────────────────────────
    const trust = r.trust_score || 0
    const trustColor = trust > 0.65 ? '#34d399' : trust > 0.35 ? '#fbbf24' : '#fb7185'
    ctx.fillStyle = 'rgba(0,0,0,0.5)'
    ctx.fillRect(8, 8, 110, 22)
    ctx.fillStyle = trustColor
    ctx.font = 'bold 10px JetBrains Mono, monospace'
    ctx.fillText(`TRUST ${Math.round(trust * 100)}%`, 12, 24)

    // ── Blink indicator ────────────────────────────────────────
    if (r.blink_detected) {
      ctx.fillStyle = 'rgba(52,211,153,0.85)'
      ctx.font = 'bold 11px Inter, sans-serif'
      ctx.fillText('👁 BLINK', vw / 2 - 28, 22)
    }

    // ── Lip movement indicator ─────────────────────────────────
    if (r.lip_moving) {
      ctx.fillStyle = 'rgba(251,191,36,0.9)'
      ctx.font = 'bold 11px Inter, sans-serif'
      ctx.fillText('🗣 TALKING', vw / 2 - 32, 40)
    }
  }

  const startSession = useCallback(async () => {
    await startCamera()
    connect()
    setRunning(true)
    intervalRef.current = setInterval(() => {
      const frame = captureFrame(0.7)
      if (frame) send({ frame })
    }, 1000 / FPS)
  }, [startCamera, connect, captureFrame, send])

  const stopSession = useCallback(async () => {
    clearInterval(intervalRef.current)
    stopCamera()
    disconnect()
    setRunning(false)
    // End session in backend
    if (sessionId) {
      try { await fetch(`/session/${sessionId}/end`, { method: 'POST' }) } catch {}
    }
  }, [stopCamera, disconnect, sessionId])

  useEffect(() => () => { clearInterval(intervalRef.current); stopCamera(); disconnect() }, [])

  const spoofColor = result?.spoof_label === 'REAL'  ? 'var(--emerald)'
                   : result?.spoof_label === 'SPOOF' ? 'var(--rose)'
                   :                                   'var(--amber)'

  const barData = {
    attention:   result?.attention_score   ?? 0,
    liveness:    result?.liveness_score    ?? 0,
    eye_contact: result?.eye_contact_score ?? 0,
    spoof_clean: result?.spoof_confidence  ?? 0.5,
  }

  return (
    <main className="page">
      {/* ── Header ──────────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-4" style={{ flexWrap: 'wrap', gap: '0.75rem' }}>
        <div>
          <h2>Candidate Session</h2>
          <p style={{ fontSize: '0.83rem', marginTop: '0.2rem' }}>
            <span style={{ color: 'var(--text-muted)' }}>ID:</span>{' '}
            <span className="mono" style={{ color: 'var(--cyan)', fontSize: '0.78rem' }}>{sessionId?.substring(0,16)}…</span>
            {' · '}<span style={{ color: 'var(--text-secondary)' }}>{candName}</span>
            {' · '}<span className="mono" style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Frame #{frameCount}</span>
          </p>
        </div>
        <div className="flex gap-3 items-center">
          <span className={`status-dot ${running && status === 'open' ? 'green' : status === 'error' ? 'red' : 'amber'}`} />
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            {running && status === 'open' ? 'Live' : status}
          </span>
          {!running
            ? <button id="session-start-btn" className="btn btn-primary" onClick={startSession}>▶ Start Session</button>
            : <button id="session-stop-btn"  className="btn btn-danger"  onClick={stopSession}>⏹ End Session</button>
          }
        </div>
      </div>

      {camErr && (
        <div style={{
          padding: '0.75rem 1rem', marginBottom: '1rem', borderRadius: 'var(--radius-sm)',
          background: 'var(--rose-dim)', border: '1px solid rgba(251,113,133,0.3)',
          color: 'var(--rose)', fontSize: '0.85rem',
        }}>⚠ Camera error: {camErr}</div>
      )}

      <div className="grid-2" style={{ alignItems: 'start' }}>
        {/* ── Left: Video + Status ────────────────────────── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {/* Video feed */}
          <div className="video-wrapper" style={{ aspectRatio: '4/3' }}>
            <video ref={videoRef} muted playsInline style={{ transform: 'scaleX(-1)' }} />
            <canvas ref={canvasRef} style={{ display: 'none' }} />
            <canvas
              ref={overlayRef}
              style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', transform: 'scaleX(-1)' }}
            />
            {!running && (
              <div style={{
                position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column',
                alignItems: 'center', justifyContent: 'center', background: 'rgba(0,0,0,0.75)',
                gap: '0.75rem',
              }}>
                <div style={{ fontSize: '3rem' }}>🎥</div>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Click "Start Session" to begin</p>
              </div>
            )}
          </div>

          {/* Status pills row */}
          <div className="card" style={{ padding: '1rem' }}>
            <div className="flex gap-3 flex-wrap">
              <div style={{ flex: 1, minWidth: 80 }}>
                <div className="label">Spoof</div>
                <span className={`pill ${result?.spoof_label === 'REAL' ? 'real' : result?.spoof_label === 'SPOOF' ? 'spoof' : 'unknown'}`}>
                  {result?.spoof_label === 'REAL'
                    ? '✓ REAL'
                    : result?.spoof_label === 'SPOOF'
                      ? `✗ ${result?.spoof_type
                          ? result.spoof_type === 'ai_face' ? 'AI FACE'
                          : result.spoof_type === 'screen_replay' ? 'SCREEN'
                          : result.spoof_type === 'no_face' ? 'NO FACE'
                          : 'PHOTO'
                          : 'SPOOF'}`
                      : '? CHECKING'}
                </span>
              </div>
              <div style={{ flex: 1, minWidth: 80 }}>
                <div className="label">Liveness</div>
                <span className={`pill ${result?.is_live ? 'live' : 'checking'}`}>
                  {result?.is_live ? '✓ Live' : '● Verifying'}
                </span>
              </div>
              <div style={{ flex: 1, minWidth: 80 }}>
                <div className="label">Gaze</div>
                <span className={`pill ${result?.gaze_direction === 'CENTER' ? 'center' : result?.gaze_direction === 'UNKNOWN' ? 'unknown' : 'away'}`}>
                  {result?.gaze_direction || 'N/A'}
                </span>
              </div>
              <div style={{ flex: 1, minWidth: 80 }}>
                <div className="label">Blinks</div>
                <span className="mono" style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--cyan)' }}>
                  {result?.total_blinks ?? '--'}
                </span>
                {result?.blink_rate_per_min > 0 && (
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    {result.blink_rate_per_min}/min
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Behavior indicators row */}
          {result && (
            <div className="card" style={{ padding: '1rem' }}>
              <div className="section-title mb-3">Behavior Indicators</div>
              <div className="flex gap-3 flex-wrap">
                <div style={{ flex: 1, minWidth: 100 }}>
                  <div className="label">Lip Movement</div>
                  <span className={`pill ${result.lip_moving ? 'away' : 'live'}`}>
                    {result.lip_moving ? '🗣 Talking' : '🤫 Silent'}
                  </span>
                </div>
                <div style={{ flex: 1, minWidth: 100 }}>
                  <div className="label">Body Movement</div>
                  <span className={`pill ${result.excessive_movement ? 'spoof' : 'live'}`}>
                    {result.excessive_movement ? '⚡ High' : '✓ Stable'}
                  </span>
                </div>
                <div style={{ flex: 1, minWidth: 100 }}>
                  <div className="label">Head Pose</div>
                  <span className={`pill ${result.head_turned ? 'away' : 'live'}`}>
                    {result.head_turned ? '⚠ Turned' : '✓ Forward'}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Head pose values */}
          {result && (
            <div className="card" style={{ padding: '1rem' }}>
              <div className="section-title mb-2">Head Pose (degrees)</div>
              <div className="grid-3" style={{ gap: '0.5rem' }}>
                {[['Pitch', result.pitch], ['Yaw', result.yaw], ['Roll', result.roll]].map(([k, v]) => (
                  <div key={k} style={{ textAlign: 'center' }}>
                    <div className="label">{k}</div>
                    <div className="mono" style={{
                      fontSize: '1.1rem', fontWeight: 700,
                      color: Math.abs(v) > 25 ? 'var(--rose)' : 'var(--cyan)',
                    }}>
                      {v?.toFixed(1) ?? '--'}°
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* ── Right: Gauges + Bars + Alerts ──────────────── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {/* Trust gauge + scores */}
          <div className="card">
            <div className="section-title mb-3">Live Analysis</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem', flexWrap: 'wrap' }}>
              <TrustGauge value={result?.trust_score ?? 0} label="Trust Score" size={140} />
              <div style={{ flex: 1, minWidth: 160 }}>
                <div className="grid-2" style={{ gap: '0.6rem' }}>
                  <ScoreBadge label="Attention" value={result?.attention_score ?? 0} accent="var(--cyan)" />
                  <ScoreBadge label="Liveness"  value={result?.liveness_score ?? 0}  accent="var(--emerald)" />
                  <ScoreBadge label="Eye Contact" value={result?.eye_contact_score ?? 0} accent="var(--violet)" />
                  <ScoreBadge label="Authenticity" value={result?.spoof_confidence ?? 0.5} accent="var(--amber)" />
                </div>
              </div>
            </div>
          </div>

          {/* Behavior bars */}
          <div className="card">
            <div className="section-title mb-3">Behavioral Metrics</div>
            <BehaviorBars data={barData} />
          </div>

          {/* Alert panel */}
          <div className="card">
            <AlertPanel alerts={alerts} maxHeight={320} />
          </div>
        </div>
      </div>
    </main>
  )
}
