import { useEffect, useState } from "react";
import { FolderPlus, Check, AlertTriangle } from "lucide-react";
import { collectionApi } from "../services/api";
import { errorMessage } from "../services/apiErrors";

// reviewIds on a collection are populated review summaries, not raw IDs.
const contains = (col, reviewId) => col.reviewIds?.some((r) => r._id === reviewId);

export default function AddToCollection({ reviewId }) {
  const [cols, setCols]       = useState(null); // null = still loading
  const [selected, setSelected] = useState("");
  const [saving, setSaving]   = useState(false);
  const [status, setStatus]   = useState(null); // { ok, text }

  useEffect(() => {
    collectionApi.getCollections()
      .then(({ data }) => setCols(data))
      .catch(() => setCols([]));
  }, []);

  if (cols === null) return null;

  if (cols.length === 0) {
    return <p className="add-to-collection-hint">Create a collection to organise this review.</p>;
  }

  const handleAdd = async () => {
    if (!selected) return;
    setSaving(true);
    setStatus(null);
    try {
      const { data } = await collectionApi.addReview(selected, reviewId);
      setCols((prev) => prev.map((c) => (c._id === data._id ? data : c)));
      setStatus({ ok: true, text: `Added to ${data.name}` });
      setSelected("");
    } catch (err) {
      setStatus({ ok: false, text: errorMessage(err, "Couldn't add to collection.") });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="add-to-collection">
      <select
        className="add-to-collection-select"
        value={selected}
        onChange={(e) => { setSelected(e.target.value); setStatus(null); }}
        disabled={saving}
      >
        <option value="">Add to collection…</option>
        {cols.map((c) => (
          <option key={c._id} value={c._id} disabled={contains(c, reviewId)}>
            {c.name}{contains(c, reviewId) ? " (added)" : ""}
          </option>
        ))}
      </select>
      <button className="btn btn-ghost" onClick={handleAdd} disabled={!selected || saving}>
        <FolderPlus size={15} /> {saving ? "Adding…" : "Add"}
      </button>
      {status && (
        <span className={`add-to-collection-status${status.ok ? "" : " is-error"}`}>
          {status.ok ? <Check size={14} /> : <AlertTriangle size={14} />} {status.text}
        </span>
      )}
    </div>
  );
}
