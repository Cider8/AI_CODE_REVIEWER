import { useState, useEffect } from "react";
import { authApi } from "../services/api";
import { AuthContext } from "./auth-context";

export const AuthProvider = ({ children }) => {
  const [user, setUser]       = useState(null);
  const [loading, setLoading] = useState(() => !!localStorage.getItem("token"));

  useEffect(() => {
    const token = localStorage.getItem("token");
    
    if(token) {
      authApi.getCurrentUser()
        .then(({data}) => setUser(data.user))
        .catch(() => {
          localStorage.removeItem("token");
          setUser(null);
        })
        .finally(() => setLoading(false));
    }
  },[])

  const login = async (email, password) => {
    const { data } = await authApi.login({ email, password });
    localStorage.setItem("token", data.token);
    setUser(data.user);
  };

  const register = async (name, email, password) => {
    const { data } = await authApi.register({ name, email, password });
    localStorage.setItem("token", data.token);
    setUser(data.user);
  };

  const logout = () => {
    localStorage.removeItem("token");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
