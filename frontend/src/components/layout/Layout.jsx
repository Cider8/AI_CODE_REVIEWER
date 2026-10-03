import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/useAuth";
import {
  LayoutDashboard, Code2, History, FolderOpen,
  User, LogOut, Cpu
} from "lucide-react";

const NAV = [
  { to: "/dashboard",   icon: LayoutDashboard, label: "Dashboard" },
  { to: "/review/new",  icon: Code2,           label: "New Review" },
  { to: "/history",     icon: History,         label: "History" },
  { to: "/collections", icon: FolderOpen,      label: "Collections" },
  { to: "/profile",     icon: User,            label: "Profile" },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => { 
    logout(); 
    navigate("/login"); 
  };

  return (
    <div className="layout-shell">
      {/* Sidebar */}
      <aside className="layout-sidebar">
        {/* Logo */}
        <div className="layout-logo">
          <Cpu size={22} color="var(--accent)" />
          <span className="layout-logo-text">KrishnaLens</span>
        </div>

        {/* Nav */}
        <nav className="layout-nav">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => "layout-nav-link" + (isActive ? " active" : "")}
            >
              <item.icon size={18} />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        {/* User + Logout */}
        <div className="layout-user-section">
          <div className="layout-user-name">{user?.name}</div>
          <button onClick={handleLogout} className="btn btn-ghost layout-logout-btn">
            <LogOut size={15} /> Logout
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="layout-main">
        <Outlet />
      </main>
    </div>
  );
}
