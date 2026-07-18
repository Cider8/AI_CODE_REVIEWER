import { useState } from "react";
import { Cpu, CheckCircle } from "lucide-react";
import Login from "./Login";
import Register from "./Register";


export default function Home() {
  const [modal, setModal] = useState(null); // 'login' | 'register' | null

  return (
    <div className="home-container">
      {/* Navbar */}
      <nav className="home-nav">
        <div className="logo">
          <Cpu size={30} color="var(--accent)" />
          <span>KrishnaLens</span>
        </div>
        <div className="nav-actions">
          <button onClick={() => setModal('login')} className="btn-text">Login</button>
          <button onClick={() => setModal('register')} className="btn-primary">Get Started</button>
        </div>
      </nav>

      {/* Hero Section */}
      <header className="hero">
        <div className="hero-content">
          <div className="hero-text">
            <h1>Elevate your code quality with AI</h1>
            <p>Select your language, paste your snippet, and get instant feedback on performance, security, and best practices.</p>
            <ul className="feature-list">
              <li><CheckCircle size={18} /> Deep Security Analysis</li>
              <li><CheckCircle size={18} /> Performance Benchmarking</li>
              <li><CheckCircle size={18} /> Clean Code Suggestions</li>
            </ul>
          </div>
          
          <div className="hero-demo-window">
            <div className="window-header">
              <div className="dots"><span></span><span></span><span></span></div>
              <div className="window-title">code-review.py</div>
            </div>
            <div className="window-body">
              <div className="demo-ui">
                <div className="demo-select">Select Language: Python</div>
                <div className="demo-code">
                  <span className="code-keyword">def</span> <span className="code-fn">analyze</span>():<br/>
                  &nbsp;&nbsp;print(<span className="code-str">"Reviewing Code..."</span>)
                </div>
                <button className="demo-btn">Submit for Review</button>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Developers Section */}
      <section className="team-section">
        <h2>Developed By</h2>
        <div className="team-grid">
          <div className="team-card">
            <div className="avatar"></div>
            <h3>Developer Name</h3>
            <p>Lead Engineer</p>
          </div>
        </div>
      </section>

      <footer className="home-footer">
        <p>&copy; 2024 CodeLens AI. All rights reserved.</p>
      </footer>

      {/* Modal Overlay */}
      {modal && (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setModal(null)}>&times;</button>
            {modal === 'login' ? <Login /> : <Register />}
            <p className="modal-switch">
              {modal === 'login' ? 
                <>Don't have an account? <span onClick={() => setModal('register')}>Sign Up</span></> : 
                <>Already have an account? <span onClick={() => setModal('login')}>Login</span></>
              }
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
