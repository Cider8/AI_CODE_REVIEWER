import axios from "axios";

const api = axios.create({ baseURL: "/api" });

// Attach JWT to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Redirect to login on 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
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
};

// Chat API — paths mirror app/routes/chat.py; the body key is `content`.
export const chatApi = {
  startSession: (reviewId) => api.post(`/chat/reviews/${reviewId}/start`),
  getMessages: (sessionId) => api.get(`/chat/sessions/${sessionId}/messages`),
  sendMessage: (sessionId, content) =>
    api.post(`/chat/sessions/${sessionId}/messages`, { content }),
};

export default api;
