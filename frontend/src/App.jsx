import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { useAuth } from "./context/useAuth";
import Layout from "./components/layout/Layout";

import Home       from "./pages/Home";
import Login      from "./pages/Login";
import Register   from "./pages/Register";
import Dashboard  from "./pages/Dashboard";
import NewReview  from "./pages/NewReview";
import ReviewDetail from "./pages/ReviewDetail";
import History    from "./pages/History";
import Collections from "./pages/Collections";
import Profile    from "./pages/Profile";

const Private = ({ children }) => {
  const { user, loading } = useAuth();
  if (loading) return <div className="app-loading">Loading...</div>;
  return user ? children : <Navigate to="/login" replace />;
};

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public */}
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          {/* Protected */}
          <Route element={<Private><Layout /></Private>}>
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="review/new" element={<NewReview />} />
            <Route path="review/:id" element={<ReviewDetail />} />
            <Route path="history" element={<History />} />
            <Route path="collections" element={<Collections />} />
            <Route path="profile" element={<Profile />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
