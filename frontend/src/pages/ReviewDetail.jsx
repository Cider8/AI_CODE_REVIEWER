import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Bug, ShieldAlert, Zap, Lightbulb, Code2, Trash2, ChevronDown, ChevronUp } from "lucide-react";
import { reviewApi } from "../services/api";
import ReviewChat from "../components/ReviewChat";

const scoreTone = (score) => (score >= 70 ? "score-good" : score >= 40 ? "score-warn" : "score-bad");

const ScoreRing = ({ score }) => (
  <div className="review-score-ring">
    <div className={`review-score-ring-outer ${scoreTone(score)}`} style={{ "--score-pct": score }}>
      <div className="review-score-ring-inner">
        <span className="review-score-ring-value">{score}</span>
      </div>
    </div>
    <span className="review-score-label">Score</span>
  </div>
);

const Section = ({ icon: Icon, title, color, tone, children, count }) => {
  const [open, setOpen] = useState(true);
  return (
    <div className="card review-section-card">
      <button className="review-section-toggle" onClick={() => setOpen(!open)}>
        <div className="review-section-title-wrap">
          <Icon size={18} color={color} />
          <span className="review-section-title">{title}</span>
          {count !== undefined && (
            <span className={`review-section-badge tone-${tone}`}>{count}</span>
          )}
        </div>
        {open ? <ChevronUp size={16} color="var(--text2)" /> : <ChevronDown size={16} color="var(--text2)" />}
      </button>
      {open && <div className="review-section-body">{children}</div>}
    </div>
  );
};

export default function ReviewDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [review, setReview]   = useState(null);
  const [loading, setLoading] = useState(true);
  const [showRefactor, setShowRefactor] = useState(false);

  useEffect(() => {
    reviewApi.getReviewById(id)
      .then(({ data }) => setReview(data))
      .finally(() => setLoading(false));
  }, [id]);

  const handleDelete = async () => {
    if (!confirm("Delete this review?")) return;
    await reviewApi.deleteReview(id);
    navigate("/history");
  };

  if (loading) return <div className="page page-subtle">Loading review...</div>;
  if (!review) return <div className="page score-bad">Review not found.</div>;

  return (
    <div className="page">
      {/* Header */}
      <div className="section-header review-header">
        <div className="section-header-copy">
          <h1 className="section-title">{review.title}</h1>
          <p className="review-header-meta">
            {review.language} · {new Date(review.createdAt).toLocaleString()}
          </p>
        </div>
        <div className="review-header-actions">
          <ScoreRing score={review.overallScore || 0} />
          <button className="btn btn-ghost btn-danger-outline" onClick={handleDelete}>
            <Trash2 size={15} />
          </button>
        </div>
      </div>

      {/* Summary */}
      <div className="card review-summary-card">
        <p className="review-summary-text">{review.summary}</p>
        <div className="review-summary-tags">
          {review.complexity?.time  && <span className="review-summary-tag">Time: {review.complexity.time}</span>}
          {review.complexity?.space && <span className="review-summary-tag">Space: {review.complexity.space}</span>}
          {review.tags?.map(t => <span key={t} className="review-summary-tag-accent">#{t}</span>)}
        </div>
      </div>

      {/* Bugs */}
      <Section icon={Bug} title="BUGS" color="var(--danger)" tone="danger" count={review.bugs?.length}>
        {review.bugs?.length === 0 ? <p className="review-empty-ok">✓ No bugs found</p> :
          review.bugs?.map((b, i) => (
            <div key={i} className="review-issue-card">
              <div className="review-issue-meta">
                <span className={`badge badge-${b.severity}`}>{b.severity}</span>
                {b.line && <span className="review-issue-line">Line {b.line}</span>}
              </div>
              <p className="review-issue-text">{b.description}</p>
              <p className="review-issue-tip">💡 {b.suggestion}</p>
            </div>
          ))
        }
      </Section>

      {/* Security */}
      <Section icon={ShieldAlert} title="SECURITY" color="var(--warning)" tone="warning" count={review.securityIssues?.length}>
        {review.securityIssues?.length === 0 ? <p className="review-empty-ok">✓ No security issues found</p> :
          review.securityIssues?.map((s, i) => (
            <div key={i} className="review-issue-card">
              <div className="review-issue-meta">
                <span className="badge badge-high">{s.type}</span>
                {s.line && <span className="review-issue-line">Line {s.line}</span>}
              </div>
              <p className="review-issue-text">{s.description}</p>
              <p className="review-issue-tip">🔧 {s.fix}</p>
            </div>
          ))
        }
      </Section>

      {/* Performance */}
      <Section icon={Zap} title="PERFORMANCE" color="var(--accent)" tone="accent" count={review.performanceIssues?.length}>
        {review.performanceIssues?.length === 0 ? <p className="review-empty-ok">✓ No performance issues</p> :
          review.performanceIssues?.map((p, i) => (
            <div key={i} className="review-issue-card">
              <span className={`badge badge-${p.impact} badge-block`}>{p.impact} impact</span>
              <p className="review-issue-text">{p.description}</p>
              <p className="review-issue-tip">⚡ {p.suggestion}</p>
            </div>
          ))
        }
      </Section>

      {/* Improvements */}
      <Section icon={Lightbulb} title="IMPROVEMENTS" color="var(--accent2)" tone="accent2" count={review.improvements?.length}>
        <ul className="review-improvements-list">
          {review.improvements?.map((tip, i) => (
            <li key={i} className="review-improvement-item">
              <span className="review-improvement-arrow">→</span> {tip}
            </li>
          ))}
        </ul>
      </Section>

      {/* Refactored Code */}
      {review.refactoredCode && (
        <div className="card">
          <button className="review-refactor-toggle" onClick={() => setShowRefactor(!showRefactor)}>
            <div className="review-section-title-wrap">
              <Code2 size={18} color="var(--accent)" />
              <span className="review-section-title">REFACTORED CODE</span>
            </div>
            {showRefactor ? <ChevronUp size={16} color="var(--text2)" /> : <ChevronDown size={16} color="var(--text2)" />}
          </button>
          {showRefactor && (
            <pre className="review-refactor-code">
              {review.refactoredCode}
            </pre>
          )}
        </div>
      )}

      {/* Follow-up chat */}
      <ReviewChat reviewId={id} />
    </div>
  );
}
