import { useEffect, useState } from "react";
import { FolderOpen, Plus, Trash2, Code2 } from "lucide-react";
import api from "../services/api";
import { useNavigate } from "react-router-dom";

export default function Collections() {
  const [cols, setCols]         = useState([]);
  const [newName, setNewName]   = useState("");
  const [newDesc, setNewDesc]   = useState("");
  const [creating, setCreating] = useState(false);
  const navigate = useNavigate();

  const fetch = () => api.get("/collections").then(({ data }) => setCols(data));
  useEffect(() => { fetch(); }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!newName.trim()) return;
    await api.post("/collections", { name: newName, description: newDesc });
    setNewName(""); setNewDesc(""); setCreating(false);
    fetch();
  };

  const handleDelete = async (id) => {
    if (!confirm("Delete collection?")) return;
    await api.delete(`/collections/${id}`);
    fetch();
  };

  return (
    <div className="page">
      <div className="page-header">
        <div className="page-header-copy">
          <h1 className="page-title">Collections</h1>
          <p className="page-sub dashboard-subtitle">Group your reviews into folders</p>
        </div>
        <button className="btn btn-primary" onClick={() => setCreating(!creating)}>
          <Plus size={16} /> New Collection
        </button>
      </div>

      {creating && (
        <div className="card collections-create-card">
          <form onSubmit={handleCreate} className="collections-form">
            <input value={newName} onChange={e => setNewName(e.target.value)} placeholder="Collection name (e.g. DSA Practice)" required />
            <input value={newDesc} onChange={e => setNewDesc(e.target.value)} placeholder="Description (optional)" />
            <div className="collections-form-actions">
              <button type="submit" className="btn btn-primary">Create</button>
              <button type="button" className="btn btn-ghost" onClick={() => setCreating(false)}>Cancel</button>
            </div>
          </form>
        </div>
      )}

      {cols.length === 0 ? (
        <div className="card collections-empty-state">
          <FolderOpen size={40} className="collections-empty-icon" />
          <p>No collections yet. Create one to organise your reviews.</p>
        </div>
      ) : (
        <div className="collections-grid">
          {cols.map((col) => (
            <div key={col._id} className="card collections-card">
              <div className="collections-card-head">
                <div className="collections-card-title">
                  <FolderOpen size={18} color="var(--accent)" />
                  <span className="collections-card-name">{col.name}</span>
                </div>
                <button className="collections-delete-btn" onClick={() => handleDelete(col._id)}>
                  <Trash2 size={14} />
                </button>
              </div>
              {col.description && <p className="collections-card-desc">{col.description}</p>}
              <div className="collections-review-list">
                {col.reviewIds?.slice(0, 3).map((r) => (
                  <div key={r._id} onClick={() => navigate(`/review/${r._id}`)} className="collections-review-item">
                    <Code2 size={13} color="var(--accent)" />
                    <span className="collections-review-text">{r.title}</span>
                    <span className="collections-review-score">{r.overallScore}</span>
                  </div>
                ))}
                {col.reviewIds?.length > 3 && (
                  <p className="collections-more-text">+{col.reviewIds.length - 3} more</p>
                )}
                {col.reviewIds?.length === 0 && (
                  <p className="collections-more-text">No reviews in this collection yet.</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
