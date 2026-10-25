import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Cpu, Loader } from "lucide-react";
import { authApi } from "../services/api";
import { errorMessage, fieldErrors } from "../services/apiErrors";
import { PASSWORD_HINT } from "../constants";
import { FieldHint, FieldErrors } from "../components/FieldNotes";

const RESEND_SECONDS = 60; // server ignores re-sends within 60 s (PR-FPW-05)
const UNAVAILABLE = "Password reset by email is not available right now. Please try again later.";
const STEP_TITLES = { email: "Reset your password", code: "Enter your code", password: "Choose a new password" };
const STEP_NUMBER = { email: 1, code: 2, password: 3 };

export default function ForgotPassword() {
  const navigate = useNavigate();
  const [step, setStep]       = useState("email");
  const [email, setEmail]     = useState(useLocation().state?.email || "");
  const [code, setCode]       = useState("");
  // Short-lived (10 min) and only valid for #24 — kept in memory, never in
  // localStorage and never sent as Authorization.
  const [resetToken, setResetToken] = useState(null);
  const [pw, setPw]           = useState({ next: "", confirm: "" });
  const [loading, setLoading] = useState(false);
  const [info, setInfo]       = useState("");
  const [error, setError]     = useState("");
  const [showCodeHint, setShowCodeHint] = useState(false);
  const [fieldErrs, setFieldErrs] = useState({});
  const [resendAt, setResendAt] = useState(0);
  const [now, setNow]         = useState(() => Date.now());

  const secondsLeft = Math.max(0, Math.ceil((resendAt - now) / 1000));

  useEffect(() => {
    if (!resendAt) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [resendAt]);

  const resetMessages = () => { setError(""); setInfo(""); setFieldErrs({}); setShowCodeHint(false); };

  // #22 — used for the first send and for "Resend code".
  const sendCode = async (e) => {
    e?.preventDefault();
    if (secondsLeft > 0 || loading) return;
    const address = email.trim();
    resetMessages(); setLoading(true);
    // The countdown runs from the moment of sending, matching the server's window.
    setResendAt(Date.now() + RESEND_SECONDS * 1000); setNow(Date.now());
    try {
      const { data } = await authApi.forgotPassword(address);
      setEmail(address);
      setInfo(data.message); // identical for known and unknown emails (PR-FPW-02)
      setCode("");
      setStep("code");
    } catch (err) {
      setResendAt(0); // nothing was sent, so allow an immediate retry
      const status = err.response?.status;
      if (status === 503) setError(UNAVAILABLE);
      else if (status === 422) setFieldErrs(fieldErrors(err));
      else setError(errorMessage(err, "Couldn't send the code. Please try again."));
    } finally {
      setLoading(false);
    }
  };

  // #23
  const verifyCode = async (e) => {
    e.preventDefault();
    if (code.length !== 6) return;
    resetMessages(); setLoading(true);
    try {
      const { data } = await authApi.verifyResetCode(email, code);
      setResetToken(data.resetToken);
      setPw({ next: "", confirm: "" });
      setStep("password");
    } catch (err) {
      // 400 covers wrong, expired, used and too-many-tries alike (PR-FPW-07).
      const status = err.response?.status;
      setError(status === 503 ? UNAVAILABLE : status === 400 || status === 422
        ? "Invalid or expired code"
        : errorMessage(err, "Couldn't check the code. Please try again."));
      setShowCodeHint(status === 400 || status === 422);
    } finally {
      setLoading(false);
    }
  };

  // #24
  const updatePassword = async (e) => {
    e.preventDefault();
    resetMessages();
    if (pw.next !== pw.confirm) return setError("Passwords don't match");
    setLoading(true);
    try {
      const { data } = await authApi.resetPassword(resetToken, pw.next);
      setResetToken(null);
      // Not signed in by this (PR-FPW-11): send them to sign in with the new password.
      navigate("/login", { replace: true, state: { notice: data.message } });
    } catch (err) {
      const status = err.response?.status;
      if (status === 422) {
        const byField = fieldErrors(err);
        setFieldErrs({ next: byField.newPassword || [] });
      } else if (status === 400) {
        // Token expired, already used or superseded: start over (PR-FPW-10/12).
        setResetToken(null);
        setStep("email");
        setError(errorMessage(err, "Your reset session has expired. Please start again."));
      } else {
        setError(status === 503 ? UNAVAILABLE : errorMessage(err, "Couldn't update your password. Please try again."));
      }
    } finally {
      setLoading(false);
    }
  };

  const backToEmail = () => { resetMessages(); setResetToken(null); setStep("email"); };

  return (
    <div className="auth-page">
      <div className="auth-card-wrap">
        <div className="auth-logo">
          <Cpu size={32} color="var(--accent)" />
          <h1 className="auth-logo-title">KrishnaLens</h1>
          <p className="auth-logo-sub">Step {STEP_NUMBER[step]} of 3</p>
        </div>

        <div className="card">
          <h2 className="auth-card-title">{STEP_TITLES[step]}</h2>

          {info && <div className="status-message status-message-success auth-notice">{info}</div>}
          {error && (
            <div className="status-banner">
              {error}
              {showCodeHint && (
                <p className="forgot-hint">After 5 wrong tries a code stops working, so use Resend code to get a new one.</p>
              )}
            </div>
          )}

          {step === "email" && (
            <form onSubmit={sendCode} className="form-stack">
              <div>
                <label className="field-label" htmlFor="fp-email">Email</label>
                <input
                  id="fp-email"
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  aria-invalid={!!fieldErrs.email}
                  aria-describedby={fieldErrs.email ? "fp-email-err" : undefined}
                  autoFocus
                  required
                />
                <FieldErrors id="fp-email-err" errors={fieldErrs.email} />
              </div>
              <button type="submit" className="btn btn-primary btn-block" disabled={loading || secondsLeft > 0}>
                {loading ? <Loader size={16} className="spin" />
                  : secondsLeft > 0 ? `Send code (${secondsLeft}s)` : "Send code"}
              </button>
            </form>
          )}

          {step === "code" && (
            <form onSubmit={verifyCode} className="form-stack">
              <p className="forgot-sent-to">Code sent to <strong>{email}</strong></p>
              <div>
                <label className="field-label" htmlFor="fp-code">6-digit code</label>
                <input
                  id="fp-code"
                  className="forgot-code-input"
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  pattern="\d{6}"
                  maxLength={6}
                  value={code}
                  onChange={e => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                  placeholder="000000"
                  autoFocus
                  required
                />
              </div>
              <button type="submit" className="btn btn-primary btn-block" disabled={loading || code.length !== 6}>
                {loading ? <Loader size={16} className="spin" /> : "Verify"}
              </button>
              <div className="forgot-actions">
                <button type="button" className="forgot-link-btn" onClick={() => sendCode()} disabled={loading || secondsLeft > 0}>
                  {secondsLeft > 0 ? `Resend code in ${secondsLeft}s` : "Resend code"}
                </button>
                <button type="button" className="forgot-link-btn" onClick={backToEmail} disabled={loading}>
                  Use a different email
                </button>
              </div>
            </form>
          )}

          {step === "password" && (
            <form onSubmit={updatePassword} className="form-stack">
              <div>
                <label className="field-label" htmlFor="fp-next">New password</label>
                <input
                  id="fp-next"
                  type="password"
                  autoComplete="new-password"
                  value={pw.next}
                  onChange={e => setPw({ ...pw, next: e.target.value })}
                  placeholder="Choose a new password"
                  aria-invalid={!!fieldErrs.next?.length}
                  aria-describedby={fieldErrs.next?.length ? "fp-next-hint fp-next-err" : "fp-next-hint"}
                  autoFocus
                  required
                />
                <FieldHint id="fp-next-hint">{PASSWORD_HINT}</FieldHint>
                <FieldErrors id="fp-next-err" errors={fieldErrs.next} />
              </div>
              <div>
                <label className="field-label" htmlFor="fp-confirm">Confirm password</label>
                <input
                  id="fp-confirm"
                  type="password"
                  autoComplete="new-password"
                  value={pw.confirm}
                  onChange={e => setPw({ ...pw, confirm: e.target.value })}
                  placeholder="Repeat new password"
                  required
                />
              </div>
              <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
                {loading ? <Loader size={16} className="spin" /> : "Update password"}
              </button>
            </form>
          )}

          <p className="auth-footer-text">
            Remembered it? <Link to="/login" className="auth-footer-link">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
