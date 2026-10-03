import { useEffect, useState } from "react";
import { FolderOpen, Plus, Trash2, Code2, Pencil, X } from "lucide-react";
import { collectionApi } from "../services/api";
import { errorMessage } from "../services/apiErrors";
import { useNavigate } from "react-router-dom";

const PREVIEW_COUNT = 3;

function CollectionCard({ col, onChange, onDelete }) {
  const [editing, setEditing]   = useState(false);
  const [name, setName]         = useState(col.name);
  const [desc, setDesc]         = useState(col.description || "");
  const [saving, setSaving]     = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [error, setError]       = useState("");
  const navigate = useNavigate();

  const startEdit = () => {
    setName(col.name); setDesc(col.description || ""); setError(""); setEditing(true);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    if (!name.trim()) return setError("Collection name cannot be empty");
    const payload = {};
    if (name.trim() !== col.name) payload.name = name.trim();
    if (desc.trim() !== (col.description || "")) payload.description = desc.trim(); // "" clears it
    if (!Object.keys(payload).length) return setEditing(false);

    setSaving(true); setError("");
    try {
      const { data } = await collectionApi.updateCollection(col._id, payload);
      onChange(data);
      setEditing(false);
    } catch (err) {
      setError(errorMessage(err, "Couldn't save the collection."));
    } finally {
      setSaving(false);
    }
  };

  const handleRemove = async (e, reviewId) => {
    e.stopPropagation();
    setError("");
    try {
      // Only takes the review out of this collection; the review itself is kept.
      const { data } = await collectionApi.removeReview(col._id, reviewId);
      onChange(data);
    } catch (err) {
      setError(errorMessage(err, "Couldn't remove the review."));
    }
  };

  const reviews = col.reviewIds || [];
  const shown = expanded ? reviews : reviews.slice(0, PREVIEW_COUNT);

  return (
    <div className="card collections-card">
      {editing ? (
        <form onSubmit={handleSave} className="collections-form collections-edit-form">
          <input value={name} onChange={e => setName(e.target.value)} placeholder="Collection name" aria-label="Collection name" autoFocus />
          <input value={desc} onChange={e => setDesc(e.target.value)} placeholder="Description (optional)" aria-label="Description" />
          <div className="collections-form-actions">
            <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? "Saving..." : "Save"}</button>
            <button type="button" className="btn btn-ghost" onClick={() => setEditing(false)} disabled={saving}>Cancel</button>
          </div>
        </form>
      ) : (
        <>
          <div className="collections-card-head">
            <div className="collections-card-title">
              <FolderOpen size={18} color="var(--accent)" />
              <span className="collections-card-name">{col.name}</span>
            </div>
            <div className="collections-card-actions">
              <button className="collections-icon-btn" onClick={startEdit} title="Rename or edit" aria-label={`Edit ${col.name}`}>
                <Pencil size={14} />
              </button>
              <button className="collections-delete-btn" onClick={() => onDelete(col._id)} title="Delete collection" aria-label={`Delete ${col.name}`}>
                <Trash2 size={14} />
              </button>
            </div>
          </div>
          {col.description && <p className="collections-card-desc">{col.description}</p>}
        </>
      )}

      {error && <p className="collections-error">{error}</p>}

      <div className="collections-review-list">
        {shown.map((r) => (
          <div key={r._id} onClick={() => navigate(`/review/${r._id}`)} className="collections-review-item">
            <Code2 size={13} color="var(--accent)" />
            <span className="collections-review-text">{r.title}</span>
            <span className="collections-review-score">{r.overallScore}</span>
            <button
              className="collections-remove-btn"
              onClick={(e) => handleRemove(e, r._id)}
              title="Remove from collection"
              aria-label={`Remove ${r.title} from ${col.name}`}
            >
              <X size={13} />
            </button>
          </div>
        ))}
        {reviews.length > PREVIEW_COUNT && (
          <button className="collections-more-text collections-more-btn" onClick={() => setExpanded(!expanded)}>
            {expanded ? "Show less" : `+${reviews.length - PREVIEW_COUNT} more`}
          </button>
        )}
        {reviews.length === 0 && (
          <p className="collections-more-text">No reviews in this collection yet.</p>
        )}
      </div>
    </div>
  );
}

export default function Collections() {
  const [cols, setCols]         = useState([]);
  const [newName, setNewName]   = useState("");
  const [newDesc, setNewDesc]   = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError]       = useState("");

  const load = () =>
    collectionApi.getCollections()
      .then(({ data }) => setCols(data))
      .catch((err) => setError(errorMessage(err, "Couldn't load your collections.")));

  useEffect(() => {
    load();
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!newName.trim()) return;
    setError("");
    try {
      await collectionApi.createCollection({ name: newName.trim(), description: newDesc.trim() || undefined });
      setNewName(""); setNewDesc(""); setCreating(false);
      load();
    } catch (err) {
      setError(errorMessage(err, "Couldn't create the collection."));
    }
  };

  const handleDelete = async (id) => {
    if (!confirm("Delete collection?")) return;
    setError("");
    try {
      await collectionApi.deleteCollection(id);
      load();
    } catch (err) {
      setError(errorMessage(err, "Couldn't delete the collection."));
    }
  };

  const replaceCol = (updated) =>
    setCols((prev) => prev.map((c) => (c._id === updated._id ? updated : c)));

  return (
    <div className="page">
      <div className="section-header">
        <div className="section-header-copy">
          <h1 className="section-title">Collections</h1>
          <p className="section-subtitle">Group your reviews into folders</p>
        </div>
        <button className="btn btn-primary" onClick={() => setCreating(!creating)}>
          <Plus size={16} /> New Collection
        </button>
      </div>

      {error && <div className="status-banner">{error}</div>}

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
            <CollectionCard key={col._id} col={col} onChange={replaceCol} onDelete={handleDelete} />
          ))}
        </div>
      )}
    </div>
  );
}
