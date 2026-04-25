import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

const FEATURES = [
  { icon: '👁️', title: 'Liveness Detection',    desc: 'EAR blink rate + head pose in real-time.' },
  { icon: '🎭', title: 'Spoof Detection',        desc: 'LBP + FFT + color heuristic to catch attacks.' },
  { icon: '🧠', title: 'Behavior Analysis',      desc: 'Iris gaze, eye contact, lip & body movement.' },
  { icon: '🚨', title: 'Live Alerts',            desc: 'Rule-based engine pushes violations instantly.' },
  { icon: '📊', title: 'Accurate Reports',       desc: 'Full %, gaze distribution & alert timeline.' },
  { icon: '🔒', title: 'Secure Pipeline',        desc: 'All CV runs server-side; frames never stored.' },
]

export default function HomePage() {
  const navigate = useNavigate()
  const [view, setView]         = useState('roles')   // 'roles' | 'candidate' | 'interviewer'
  const [name, setName]         = useState('')
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState('')

  async function handleCandidateStart(e) {
    e.preventDefault()
    if (!name.trim()) { setError('Please enter your name'); return }
    setLoading(true); setError('')
    try {
      const res = await fetch('/session/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ candidate_name: name.trim(), role: 'candidate' }),
      })
      const data = await res.json()
      sessionStorage.setItem('session_id',     data.session_id)
      sessionStorage.setItem('candidate_name', data.candidate_name)
      sessionStorage.setItem('role',           'candidate')
      navigate('/candidate')
    } catch {
      setError('Backend not reachable. Start the FastAPI server first.')
    } finally {
      setLoading(false)
    }
  }

  function handleInterviewerLogin(e) {
    e.preventDefault()
    sessionStorage.setItem('role', 'interviewer')
    navigate('/interviewer')
  }

  return (
    <main className="page" style={{ paddingTop: '3rem' }}>
      {/* ── Hero ──────────────────────────────────────────────── */}
      <section className="text-center" style={{ marginBottom: '3.5rem' }}>
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: '0.5rem',
          padding: '0.35rem 1rem', borderRadius: '999px',
          background: 'var(--cyan-dim)', border: '1px solid var(--border-bright)',
          fontSize: '0.78rem', fontWeight: 600, color: 'var(--cyan)',
          marginBottom: '1.5rem', letterSpacing: '0.07em', textTransform: 'uppercase',
        }}>
          <span className="status-dot cyan" />  AI-Powered • Real-Time • Accurate
        </div>

        <h1 style={{ marginBottom: '1rem' }}>
          Antispoofing{' '}
          <span className="gradient-text">Interview</span> System
        </h1>
        <p style={{ maxWidth: 520, margin: '0 auto 2.5rem', fontSize: '1.05rem' }}>
          Real-time liveness, spoof detection, gaze tracking and behavioral analysis
          — powered by MediaPipe computer vision.
        </p>

        {/* ── Role selector ─────────────────────────────────── */}
        {view === 'roles' && (
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '1.5rem',
            maxWidth: 600,
            margin: '0 auto',
          }}>
            {/* Candidate card */}
            <div
              className="role-card candidate"
              id="role-candidate-btn"
              onClick={() => setView('candidate')}
            >
              <div className="role-icon candidate">🎥</div>
              <div>
                <h2 style={{ color: 'var(--cyan)', marginBottom: '0.4rem' }}>I'm a Candidate</h2>
                <p style={{ fontSize: '0.88rem' }}>
                  Join the interview session. Your face, gaze and behavior will be monitored.
                </p>
              </div>
              <button className="btn btn-primary" style={{ width: '100%' }}>
                Start Session →
              </button>
            </div>

            {/* Interviewer card */}
            <div
              className="role-card interviewer"
              id="role-interviewer-btn"
              onClick={() => setView('interviewer')}
            >
              <div className="role-icon interviewer">📋</div>
              <div>
                <h2 style={{ color: 'var(--violet)', marginBottom: '0.4rem' }}>I'm an Interviewer</h2>
                <p style={{ fontSize: '0.88rem' }}>
                  Monitor all candidate sessions, view live metrics and download reports.
                </p>
              </div>
              <button className="btn btn-violet" style={{ width: '100%' }}>
                Open Dashboard →
              </button>
            </div>
          </div>
        )}

        {/* ── Candidate form ─────────────────────────────────── */}
        {view === 'candidate' && (
          <div style={{ maxWidth: 400, margin: '0 auto' }}>
            <button
              className="btn btn-secondary"
              style={{ marginBottom: '1.5rem', fontSize: '0.82rem' }}
              onClick={() => { setView('roles'); setError(''); setName('') }}
            >
              ← Back
            </button>
            <div className="card" style={{ padding: '2rem' }}>
              <div className="role-icon candidate" style={{ margin: '0 auto 1.5rem', width: 60, height: 60, fontSize: '1.6rem' }}>🎥</div>
              <h3 style={{ textAlign: 'center', marginBottom: '0.4rem' }}>Enter Your Name</h3>
              <p style={{ textAlign: 'center', fontSize: '0.85rem', marginBottom: '1.5rem' }}>
                Your name will appear in the session report.
              </p>
              <form onSubmit={handleCandidateStart} style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                <input
                  id="candidate-name-input"
                  className="input"
                  type="text"
                  placeholder="Enter your full name…"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  autoFocus
                  autoComplete="name"
                />
                {error && <p style={{ color: 'var(--rose)', fontSize: '0.82rem' }}>{error}</p>}
                <button id="start-candidate-btn" className="btn btn-primary w-full" type="submit" disabled={loading}>
                  {loading
                    ? <><span className="spinner" style={{ width: 18, height: 18 }} /> Starting…</>
                    : '🎥 Start Interview Session'
                  }
                </button>
              </form>
            </div>
          </div>
        )}

        {/* ── Interviewer quick-enter ─────────────────────────── */}
        {view === 'interviewer' && (
          <div style={{ maxWidth: 400, margin: '0 auto' }}>
            <button
              className="btn btn-secondary"
              style={{ marginBottom: '1.5rem', fontSize: '0.82rem' }}
              onClick={() => setView('roles')}
            >
              ← Back
            </button>
            <div className="card" style={{ padding: '2rem', textAlign: 'center' }}>
              <div className="role-icon interviewer" style={{ margin: '0 auto 1.5rem', width: 60, height: 60, fontSize: '1.6rem' }}>📋</div>
              <h3 style={{ marginBottom: '0.4rem' }}>Interviewer Dashboard</h3>
              <p style={{ fontSize: '0.85rem', marginBottom: '1.5rem' }}>
                Monitor all active and past candidate sessions with live metrics and reports.
              </p>
              <form onSubmit={handleInterviewerLogin}>
                <button id="goto-interviewer-btn" className="btn btn-violet w-full" type="submit">
                  📋 Open Dashboard →
                </button>
              </form>
            </div>
          </div>
        )}
      </section>

      {/* ── Features grid ─────────────────────────────────────── */}
      {view === 'roles' && (
        <>
          <section>
            <p className="section-title text-center mb-4">What This System Detects</p>
            <div className="grid-3">
              {FEATURES.map(f => (
                <div key={f.title} className="card" style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '2rem', marginBottom: '0.75rem' }}>{f.icon}</div>
                  <h3 style={{ marginBottom: '0.4rem' }}>{f.title}</h3>
                  <p style={{ fontSize: '0.85rem' }}>{f.desc}</p>
                </div>
              ))}
            </div>
          </section>

          {/* Pipeline diagram */}
          <section className="card" style={{ marginTop: '2rem', padding: '1.5rem' }}>
            <p className="section-title mb-3">Analysis Pipeline</p>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap' }}>
              {['Webcam','Face Detect','Landmarks','Liveness','Spoof','Gaze + Behavior','Trust Score','Alerts','Report'].map((step, i, arr) => (
                <span key={step} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <span style={{
                    padding: '0.35rem 0.75rem', borderRadius: '6px',
                    background: i === 0 ? 'var(--cyan-dim)' : i === arr.length-1 ? 'var(--violet-dim)' : 'var(--bg-card-2)',
                    border: `1px solid ${i === 0 ? 'rgba(56,189,248,0.3)' : i === arr.length-1 ? 'rgba(167,139,250,0.3)' : 'var(--border)'}`,
                    fontSize: '0.78rem', fontWeight: 600,
                    color: i === 0 ? 'var(--cyan)' : i === arr.length-1 ? 'var(--violet)' : 'var(--text-secondary)',
                  }}>{step}</span>
                  {i < arr.length - 1 && <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>→</span>}
                </span>
              ))}
            </div>
          </section>
        </>
      )}
    </main>
  )
}
