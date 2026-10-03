import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/useAuth";
import { Cpu, Loader } from "lucide-react";
import { errorMessage } from "../services/apiErrors";

export default function Login() {
  const [form, setForm]   = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login }   = useAuth();
  const navigate    = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      await login(form.email, form.password);
      navigate("/dashboard");
    } catch (err) {
      setError(errorMessage(err, "Login failed"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card-wrap">
        {/* Logo */}
        <div className="auth-logo">
          <Cpu size={32} color="var(--accent)" />
          <h1 className="auth-logo-title">KrishnaLens</h1>
          <p className="auth-logo-sub">AI-powered code review</p>
        </div>

        <div className="card">
          <h2 className="auth-card-title">Sign in</h2>

          {error && <div className="status-banner">{error}</div>}

          <form onSubmit={handleSubmit} className="form-stack">
            <div>
              <label className="field-label">Email</label>
              <input type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} placeholder="you@example.com" required />
            </div>
            <div>
              <label className="field-label">Password</label>
              <input type="password" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} placeholder="••••••••" required />
            </div>
            <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
              {loading ? <Loader size={16} className="spin" /> : "Sign in"}
            </button>
          </form>

          <p className="auth-footer-text">
            No account? <Link to="/register" className="auth-footer-link">Create one</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
