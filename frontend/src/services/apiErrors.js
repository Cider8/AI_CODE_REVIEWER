// FastAPI sends `detail` as a string for HTTPException, but as an array of
// { loc, msg } objects for 422 validation errors.

const UNAVAILABLE = "The service is temporarily unavailable. Please try again later.";

// 503 (database down) or no response at all (server unreachable).
export const unavailableMessage = (err) =>
  err && (!err.response || err.response.status === 503) ? UNAVAILABLE : null;

export const errorMessage = (err, fallback) => {
  const down = unavailableMessage(err);
  if (down) return down;
  const detail = err?.response?.data?.detail;
  return typeof detail === "string" ? detail : fallback;
};

// Pydantic prefixes custom validator messages with "Value error, ", and the
// password validator joins every failed rule with "; ".
const toRules = (msg) => msg.replace(/^Value error,\s*/, "").split("; ").filter(Boolean);

// Maps a 422 detail array to { [fieldName]: [message, ...] }, keyed by the
// last `loc` segment (e.g. "password", "newPassword", "email").
export const fieldErrors = (err) => {
  const detail = err?.response?.data?.detail;
  if (!Array.isArray(detail)) return {};
  const out = {};
  for (const { loc, msg } of detail) {
    const field = Array.isArray(loc) ? loc[loc.length - 1] : null;
    if (!field || typeof msg !== "string") continue;
    out[field] = [...(out[field] || []), ...toRules(msg)];
  }
  return out;
};
