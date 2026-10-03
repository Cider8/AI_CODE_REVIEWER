import { useState } from "react";
import { useAuth } from "../context/useAuth";
import { User, Save, Lock, Loader } from "lucide-react";
import { authApi } from "../services/api";
import { LANGUAGES, PASSWORD_HINT } from "../constants";
import { errorMessage, fieldErrors } from "../services/apiErrors";
import { FieldHint, FieldErrors } from "../components/FieldNotes";

// The change-password 422 reports fields by their API names.
const PW_FIELDS = { currentPassword: "current", newPassword: "next" };


const Msg = ({ msg }) => msg.text ? (
  <div className={`status-message ${msg.ok ? "status-message-success" : "status-message-danger"}`}>
    {msg.text}
  </div>
) : null;

export default function Profile() {
  const { user, logout, updateUser } = useAuth();

  // Profile section
  const [name, setName]   = useState(user?.name || "");
  const [langs, setLangs] = useState(user?.preferredLanguages || []);
  const [profileMsg, setProfileMsg] = useState({ text: "", ok: true });
  const [savingProfile, setSavingProfile] = useState(false);

  // Password section
  const [pwForm, setPwForm] = useState({ current: "", next: "", confirm: "" });
  const [pwMsg, setPwMsg]   = useState({ text: "", ok: true });
  const [pwErrs, setPwErrs] = useState({}); // 422 messages keyed by form field
  const [savingPw, setSavingPw] = useState(false);

  // Delete section
  const [deleting, setDeleting] = useState(false);

  const toggleLang = (lang) =>
    setLangs(prev => prev.includes(lang) ? prev.filter(l => l !== lang) : [...prev, lang]);

  const handleSaveProfile = async (e) => {
    e.preventDefault();
    setSavingProfile(true); setProfileMsg({ text: "", ok: true });
    try {
      const { data } = await authApi.updateProfile({ name, preferredLanguages: langs });
      updateUser(data);
      setProfileMsg({ text: "Profile saved!", ok: true });
    } catch (err) {
      setProfileMsg({ text: errorMessage(err, "Save failed"), ok: false });
    } finally {
      setSavingProfile(false);
      setTimeout(() => setProfileMsg({ text: "", ok: true }), 3000);
    }
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    if (pwForm.next !== pwForm.confirm)
      return setPwMsg({ text: "Passwords don't match", ok: false });
    setSavingPw(true); setPwMsg({ text: "", ok: true }); setPwErrs({});
    try {
      await authApi.changePassword({ currentPassword: pwForm.current, newPassword: pwForm.next });
      setPwMsg({ text: "Password changed!", ok: true });
      setPwForm({ current: "", next: "", confirm: "" });
    } catch (err) {
      const byField = {};
      for (const [field, msgs] of Object.entries(fieldErrors(err)))
        byField[PW_FIELDS[field] || field] = msgs;
      setPwErrs(byField);
      if (!Object.keys(byField).length)
        setPwMsg({ text: errorMessage(err, "Couldn't change your password."), ok: false });
    } finally {
      setSavingPw(false);
      setTimeout(() => setPwMsg({ text: "", ok: true }), 3000);
    }
  };

  const handleDeleteAccount = async () => {
    if (!confirm("This will permanently delete your account and ALL your reviews. Are you sure?")) return;
    if (!confirm("Last chance — this cannot be undone!")) return;
    setDeleting(true);
    try {
      await authApi.deleteAccount();
      logout();
    } catch {
      alert("Delete failed. Try again.");
      setDeleting(false);
    }
  };

  return (
    <div className="page page-narrow">
      <h1 className="section-title">Profile</h1>
      <p className="section-subtitle">Manage your account</p>

      {/* ── Profile Info ── */}
      <div className="card card-mb">
        <div className="profile-section-head">
          <div className="avatar">
            <User size={22} color="#fff" />
          </div>
          <div>
            <div className="profile-name">{user?.name}</div>
            <div className="profile-email">{user?.email}</div>
          </div>
        </div>

        <form onSubmit={handleSaveProfile} className="form-stack form-stack-lg">
          <div>
            <label className="field-label">Display Name</label>
            <input value={name} onChange={e => setName(e.target.value)} placeholder="Your name" required />
          </div>

          <div>
            <label className="field-label">Preferred Languages</label>
            <div className="chip-toggle-row">
              {LANGUAGES.map(lang => (
                <button
                  type="button"
                  key={lang}
                  onClick={() => toggleLang(lang)}
                  className={`chip-toggle${langs.includes(lang) ? " active" : ""}`}
                >
                  {lang}
                </button>
              ))}
            </div>
          </div>

          <div>
            <button type="submit" className="btn btn-primary" disabled={savingProfile}>
              {savingProfile ? <Loader size={15} className="spin" /> : <Save size={15} />}
              {savingProfile ? "Saving..." : "Save Profile"}
            </button>
            <Msg msg={profileMsg} />
          </div>
        </form>
      </div>

      {/* ── Change Password ── */}
      <div className="card card-mb">
        <div className="profile-section-head-sm">
          <Lock size={16} color="var(--accent)" />
          <h3 className="profile-section-title">Change Password</h3>
        </div>

        <form onSubmit={handleChangePassword} className="form-stack form-stack-sm">
          {[
            { key: "current", label: "Current Password",  placeholder: "Your current password" },
            { key: "next",    label: "New Password",      placeholder: "Choose a new password", hint: PASSWORD_HINT },
            { key: "confirm", label: "Confirm Password",  placeholder: "Repeat new password" },
          ].map(({ key, label, placeholder, hint }) => (
            <div key={key}>
              <label className="field-label" htmlFor={`pw-${key}`}>{label}</label>
              <input
                id={`pw-${key}`}
                type="password"
                value={pwForm[key]}
                onChange={e => setPwForm({ ...pwForm, [key]: e.target.value })}
                placeholder={placeholder}
                aria-invalid={!!pwErrs[key]}
                aria-describedby={[hint && `pw-${key}-hint`, pwErrs[key] && `pw-${key}-err`].filter(Boolean).join(" ") || undefined}
                required
              />
              {hint && <FieldHint id={`pw-${key}-hint`}>{hint}</FieldHint>}
              <FieldErrors id={`pw-${key}-err`} errors={pwErrs[key]} />
            </div>
          ))}
          <div>
            <button type="submit" className="btn btn-ghost" disabled={savingPw}>
              {savingPw ? <Loader size={15} className="spin" /> : <Lock size={15} />}
              {savingPw ? "Updating..." : "Update Password"}
            </button>
            <Msg msg={pwMsg} />
          </div>
        </form>
      </div>

      {/* ── Danger Zone ── */}
      <div className="card card-danger-outline">
        <h3 className="profile-danger-title">Danger Zone</h3>
        <p className="profile-danger-copy">
          Permanently deletes your account, all reviews, stats, and collections. This cannot be undone.
        </p>
        <button className="btn btn-danger profile-danger-btn" onClick={handleDeleteAccount} disabled={deleting}>
          {deleting ? <Loader size={14} className="spin" /> : null}
          {deleting ? "Deleting..." : "Delete My Account"}
        </button>
      </div>
    </div>
  );
}
