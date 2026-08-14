import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Code2, Search, Trash2 } from "lucide-react";
import { reviewApi } from "../services/api";

const LANGUAGES = ["All","JavaScript","TypeScript","Python","Java","C++","Go","Rust","Ruby","PHP"];

export default function History() {
  const [reviews, setReviews] = useState([]);
  const [total, setTotal]     = useState(0);
  const [page, setPage]       = useState(1);
  const [search, setSearch]   = useState("");
  const [lang, setLang]       = useState("All");
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const fetchReviews = async () => {
    setLoading(true);
    try {
      const params = { page, limit: 10 };
      if (search) params.search = search;
      if (lang !== "All") params.language = lang;
      const { data } = await reviewApi.getReviews(params);
      setReviews(data.reviews);
      setTotal(data.total);
    } finally {
      setLoading(false);
    }
  };

  // Loading flag is set inside fetchReviews before the request starts;
  // the rule can't see across the function call, so it's suppressed here.
  // eslint-disable-next-line react-hooks/set-state-in-effect, react-hooks/exhaustive-deps
  useEffect(() => { fetchReviews(); }, [page, lang]);

  const handleSearch = (e) => { e.preventDefault(); setPage(1); fetchReviews(); };

  const scoreTone = (score) => (score >= 70 ? "score-good" : score >= 40 ? "score-warn" : "score-bad");

  const handleDelete = async (e, id) => {
    e.stopPropagation();
    if (!confirm("Delete this review?")) return;
    await reviewApi.deleteReview(id);
    fetchReviews();
  };

  return (
    <div className="page">
      <h1 className="section-title">History</h1>
      <p className="section-subtitle">All your past code reviews</p>

      {/* Filters */}
      <div className="history-filters">
        <form onSubmit={handleSearch} className="history-search-form">
          <div className="history-search-wrap">
            <Search size={15} className="history-search-icon" />
            <input className="history-search-input" value={search} onChange={e => setSearch(e.target.value)} placeholder="Search reviews..." />
          </div>
          <button type="submit" className="btn btn-ghost">Search</button>
        </form>
        <select className="history-select" value={lang} onChange={e => { setLang(e.target.value); setPage(1); }}>
          {LANGUAGES.map(l => <option key={l}>{l}</option>)}
        </select>
      </div>

      {loading ? (
        <div className="history-loading">Loading...</div>
      ) : reviews.length === 0 ? (
        <div className="card history-empty-card">
          <Code2 size={40} className="history-empty-icon" />
          <p>No reviews found. <span className="history-empty-link" onClick={() => navigate("/review/new")}>Submit your first code →</span></p>
        </div>
      ) : (
        <>
          <div className="history-list">
            {reviews.map((r) => (
              <div key={r._id} onClick={() => navigate(`/review/${r._id}`)} className="card history-review-card">
                <div className="history-review-main">
                  <div className="history-review-icon-wrap">
                    <Code2 size={16} color="var(--accent)" />
                  </div>
                  <div>
                    <div className="history-review-title">{r.title}</div>
                    <div className="history-review-meta">
                      {r.language} · {new Date(r.createdAt).toLocaleDateString()}
                    </div>
                  </div>
                </div>
                <div className="history-review-actions">
                  <div className={`history-score ${scoreTone(r.overallScore)}`}>
                    {r.overallScore ?? "—"}
                  </div>
                  <button className="history-delete-btn" onClick={(e) => handleDelete(e, r._id)}>
                    <Trash2 size={15} />
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          {total > 10 && (
            <div className="history-pagination">
              <button className="btn btn-ghost" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>← Prev</button>
              <span className="history-pagination-label">Page {page} of {Math.ceil(total / 10)}</span>
              <button className="btn btn-ghost" onClick={() => setPage(p => p + 1)} disabled={page >= Math.ceil(total / 10)}>Next →</button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
