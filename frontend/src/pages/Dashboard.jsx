import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { Code2, Bug, ShieldAlert, Star, Plus } from "lucide-react";
import api from "../services/api";

const COLORS = ["#7c6aff", "#00e5b0", "#ff4d6a", "#ffb347", "#60a5fa"];

export default function Dashboard() {
  const [data, setData]     = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/stats").then(({ data }) => setData(data)).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="page page-subtle">Loading dashboard...</div>;
  if (!data)   return <div className="page score-bad">Failed to load stats.</div>;

  const { stats, recentReviews } = data;

  const scoreData = stats.scoreHistory.slice(-10).map((s, i) => ({
    review: `#${i + 1}`,
    score: s.score,
  }));

  const scoreTone = (score) => (score >= 70 ? "score-good" : score >= 40 ? "score-warn" : "score-bad");

  const statCards = [
    { label: "Total Reviews",    value: stats.totalReviews,             icon: Code2,       color: "var(--accent)",  tone: "accent" },
    { label: "Average Score",    value: `${stats.averageScore}/100`,    icon: Star,        color: "var(--accent2)", tone: "accent2" },
    { label: "Bugs Found",       value: stats.totalBugsFound,           icon: Bug,         color: "var(--danger)",  tone: "danger" },
    { label: "Security Issues",  value: stats.totalSecurityIssuesFound, icon: ShieldAlert, color: "var(--warning)", tone: "warning" },
  ];

  return (
    <div className="page">
      <div className="page-header dashboard-header">
        <div className="page-header-copy">
          <h1 className="page-title">Dashboard</h1>
          <p className="page-sub dashboard-subtitle">Your code quality at a glance</p>
        </div>
        <button className="btn btn-primary" onClick={() => navigate("/review/new")}>
          <Plus size={16} /> New Review
        </button>
      </div>

      {/* Stat cards */}
      <div className="page-grid-4 dashboard-stats">
        {statCards.map(({ label, value, icon: Icon, color, tone }) => (
          <div key={label} className="card dashboard-stat-card">
            <div className={`dashboard-stat-icon dashboard-stat-icon-${tone}`}>
              <Icon size={20} color={color} />
            </div>
            <div>
              <div className="dashboard-stat-value">{value}</div>
              <div className="dashboard-stat-label">{label}</div>
            </div>
          </div>
        ))}
      </div>

      <div className="page-grid-2 dashboard-panels">
        {/* Score over time */}
        <div className="card">
          <h3 className="dashboard-section-label">SCORE OVER TIME</h3>
          {scoreData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={scoreData}>
                <XAxis dataKey="review" stroke="var(--text2)" fontSize={11} />
                <YAxis domain={[0, 100]} stroke="var(--text2)" fontSize={11} />
                <Tooltip contentStyle={{ background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 8 }} />
                <Line type="monotone" dataKey="score" stroke="var(--accent)" strokeWidth={2} dot={{ fill: "var(--accent)", r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="dashboard-empty-state">
              No reviews yet. Submit your first code!
            </div>
          )}
        </div>

        {/* Language breakdown */}
        <div className="card">
          <h3 className="dashboard-section-label">LANGUAGES</h3>
          {stats.languageBreakdown.length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={150}>
                <PieChart>
                  <Pie data={stats.languageBreakdown} dataKey="count" nameKey="language" cx="50%" cy="50%" outerRadius={60}>
                    {stats.languageBreakdown.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 8 }} />
                </PieChart>
              </ResponsiveContainer>
              <div className="dashboard-language-wrap">
                {stats.languageBreakdown.map((l, i) => (
                  <span key={l.language} className={`dashboard-language-chip chip-color-${i % COLORS.length}`}>
                    <span className={`dashboard-language-dot dot-color-${i % COLORS.length}`} />
                    {l.language} ({l.count})
                  </span>
                ))}
              </div>
            </>
          ) : (
            <div className="dashboard-empty-state dashboard-empty-state-sm">No data yet</div>
          )}
        </div>
      </div>

      {/* Recent reviews */}
      <div className="card">
        <h3 className="dashboard-section-label dashboard-section-label-mb">RECENT REVIEWS</h3>
        {recentReviews.length === 0 ? (
          <p className="page-muted">No reviews yet.</p>
        ) : (
          <div className="dashboard-recent-list">
            {recentReviews.map((r) => (
              <div key={r._id} onClick={() => navigate(`/review/${r._id}`)} className="dashboard-recent-item">
                <div className="dashboard-recent-main">
                  <Code2 size={16} color="var(--accent)" />
                  <div>
                    <div className="dashboard-recent-title">{r.title}</div>
                    <div className="dashboard-recent-meta">{r.language} · {new Date(r.createdAt).toLocaleDateString()}</div>
                  </div>
                </div>
                <div className={`dashboard-score ${scoreTone(r.overallScore)}`}>
                  {r.overallScore}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
