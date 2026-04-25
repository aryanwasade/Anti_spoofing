import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import HomePage        from './pages/HomePage.jsx'
import CandidatePage   from './pages/CandidatePage.jsx'
import InterviewerPage from './pages/InterviewerPage.jsx'

function Navbar() {
  const loc = useLocation()
  return (
    <nav className="navbar">
      <Link to="/" className="navbar-brand">
        <div className="navbar-logo">🛡️</div>
        <span>AntiSpoof <span className="gradient-text">Interview</span></span>
      </Link>
      <ul className="navbar-links">
        <li><Link to="/"           className={loc.pathname === '/'            ? 'active' : ''}>Home</Link></li>
        <li><Link to="/candidate"  className={loc.pathname === '/candidate'   ? 'active' : ''}>Candidate</Link></li>
        <li><Link to="/interviewer"className={loc.pathname === '/interviewer'  ? 'active' : ''}>Interviewer</Link></li>
      </ul>
    </nav>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <Routes>
        <Route path="/"            element={<HomePage />} />
        <Route path="/candidate"   element={<CandidatePage />} />
        <Route path="/interviewer" element={<InterviewerPage />} />
      </Routes>
    </BrowserRouter>
  )
}
