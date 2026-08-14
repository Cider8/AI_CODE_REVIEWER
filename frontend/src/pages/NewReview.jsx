import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Loader, Sparkles } from "lucide-react";
import { reviewApi } from "../services/api";

const LANGUAGES = ["JavaScript","TypeScript","Python","Java","C++","C","Go","Rust","Ruby","PHP","Swift","Kotlin","C#"];

export default function NewReview() {
  const [form, setForm] = useState({ title: "", language: "JavaScript", code: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.code.trim()) return setError("Please paste some code first.");
    setError(""); setLoading(true);
    try {
      const { data } = await reviewApi.createReview({
        title: form.title || undefined,
        language: form.language,
        originalCode: form.code,
      });
      navigate(`/review/${data._id}`);
    } catch (err) {
      setError(err.response?.data?.message || "Analysis failed. Try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page new-review-page">
      <h1 className="section-title">New Review</h1>
      <p className="section-subtitle">Paste your code and let AI find bugs, security issues, and improvements.</p>

      {error && (
        <div className="status-banner">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="new-review-form">
        <div className="new-review-grid">
          <div>
            <label className="field-label">Title (optional)</label>
            <input value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} placeholder="e.g. Binary Search Implementation" />
          </div>
          <div>
            <label className="field-label">Language</label>
            <select className="new-review-select" value={form.language} onChange={e => setForm({ ...form, language: e.target.value })}>
              {LANGUAGES.map(l => <option key={l} value={l}>{l}</option>)}
            </select>
          </div>
        </div>

        <div>
          <label className="field-label">Code</label>
          <textarea
            value={form.code}
            onChange={e => setForm({ ...form, code: e.target.value })}
            placeholder={`// Paste your ${form.language} code here...`}
            rows={22}
            className="new-review-textarea"
            required
          />
        </div>

        <button type="submit" className="btn btn-primary new-review-submit" disabled={loading}>
          {loading ? (
            <><Loader size={16} className="spin" /> Analyzing...</>
          ) : (
            <><Sparkles size={16} /> Analyze with AI</>
          )}
        </button>
      </form>

      {loading && (
        <div className="new-review-status-card">
          <div className="new-review-status-title">🤖 AI is reviewing your code...</div>
          <div className="new-review-status-copy">Checking for bugs, security issues, and performance problems</div>
        </div>
      )}
    </div>
  );
}
