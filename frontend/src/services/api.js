import axios from "axios";

const api = axios.create({ baseURL: "/api" });

// Attach JWT to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Redirect to login on 401. Login is the one endpoint where 401 means
// "wrong credentials" rather than an invalid session, so the page shows it.
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && err.config?.url !== "/auth/login") {
      localStorage.removeItem("token");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export const authApi = {
  getCurrentUser: () => api.get("/auth/me"),
  login: (payload) => api.post("/auth/login", payload),
  register: (payload) => api.post("/auth/register", payload),
  updateProfile: (payload) => api.patch("/auth/profile", payload),
  changePassword: (payload) => api.patch("/auth/password", payload),
  deleteAccount: () => api.delete("/auth/account"),
};

export const reviewApi = {
  createReview: (payload) => api.post("/reviews", payload),
  getReviews: (params = {}) => api.get("/reviews", { params }),
  getReviewById: (id) => api.get(`/reviews/${id}`),
  deleteReview: (id) => api.delete(`/reviews/${id}`),
};

export const statsApi = {
  getDashboardStats: () => api.get("/stats"),
};

export const collectionApi = {
  getCollections: () => api.get("/collections"),
  createCollection: (payload) => api.post("/collections", payload),
  deleteCollection: (id) => api.delete(`/collections/${id}`),
  // Idempotent; returns the updated collection with reviewIds populated.
  addReview: (collectionId, reviewId) =>
    api.patch(`/collections/${collectionId}/add-review`, { reviewId }),
  // Never deletes the review itself; removing an absent ID is a no-op.
  removeReview: (collectionId, reviewId) =>
    api.patch(`/collections/${collectionId}/remove-review`, { reviewId }),
  // payload: { name?, description? }; description "" clears it.
  updateCollection: (collectionId, payload) =>
    api.patch(`/collections/${collectionId}`, payload),
};

// Chat API — paths mirror app/routes/chat.py; the body key is `content`.
export const chatApi = {
  startSession: (reviewId) => api.post(`/chat/reviews/${reviewId}/start`),
  getMessages: (sessionId) => api.get(`/chat/sessions/${sessionId}/messages`),
  sendMessage: (sessionId, content) =>
    api.post(`/chat/sessions/${sessionId}/messages`, { content }),
};

export default api;
