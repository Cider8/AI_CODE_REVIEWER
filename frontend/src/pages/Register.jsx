import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/useAuth";
import { Cpu, Loader } from "lucide-react";

export default function Register() {
  const [form, setForm]   = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate     = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      await register(form.name, form.email, form.password);
      navigate("/dashboard");
    } catch (err) {
      setError(err.response?.data?.message || "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card-wrap">
        <div className="auth-logo">
          <Cpu size={32} color="var(--accent)" />
          <h1 className="auth-logo-title">KrishnaLens</h1>
          <p className="auth-logo-sub">Start reviewing smarter</p>
        </div>

        <div className="card">
          <h2 className="auth-card-title">Create account</h2>

          {error && <div className="status-banner">{error}</div>}

          <form onSubmit={handleSubmit} className="form-stack">
            {[
              { key: "name",     label: "Name",     type: "text",     placeholder: "Your name" },
              { key: "email",    label: "Email",    type: "email",    placeholder: "you@example.com" },
              { key: "password", label: "Password", type: "password", placeholder: "Min 6 characters" },
            ].map(({ key, label, type, placeholder }) => (
              <div key={key}>
                <label className="field-label">{label}</label>
                <input type={type} value={form[key]} onChange={e => setForm({ ...form, [key]: e.target.value })} placeholder={placeholder} required />
              </div>
            ))}
            <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
              {loading ? <Loader size={16} className="spin" /> : "Create account"}
            </button>
          </form>

          <p className="auth-footer-text">
            Have an account? <Link to="/login" className="auth-footer-link">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
