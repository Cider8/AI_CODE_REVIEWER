import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/useAuth";
import { Cpu, Loader } from "lucide-react";
import { errorMessage, fieldErrors } from "../services/apiErrors";
import { PASSWORD_HINT } from "../constants";
import { FieldHint, FieldErrors } from "../components/FieldNotes";

export default function Register() {
  const [form, setForm]   = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [fieldErrs, setFieldErrs] = useState({}); // 422 messages keyed by field
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate     = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(""); setFieldErrs({}); setLoading(true);
    try {
      await register(form.name, form.email, form.password);
      navigate("/dashboard");
    } catch (err) {
      const byField = fieldErrors(err);
      setFieldErrs(byField);
      if (!Object.keys(byField).length) setError(errorMessage(err, "Registration failed"));
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
              { key: "password", label: "Password", type: "password", placeholder: "Choose a password", hint: PASSWORD_HINT },
            ].map(({ key, label, type, placeholder, hint }) => (
              <div key={key}>
                <label className="field-label" htmlFor={`reg-${key}`}>{label}</label>
                <input
                  id={`reg-${key}`}
                  type={type}
                  value={form[key]}
                  onChange={e => setForm({ ...form, [key]: e.target.value })}
                  placeholder={placeholder}
                  aria-invalid={!!fieldErrs[key]}
                  aria-describedby={[hint && `reg-${key}-hint`, fieldErrs[key] && `reg-${key}-err`].filter(Boolean).join(" ") || undefined}
                  required
                />
                {hint && <FieldHint id={`reg-${key}-hint`}>{hint}</FieldHint>}
                <FieldErrors id={`reg-${key}-err`} errors={fieldErrs[key]} />
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
