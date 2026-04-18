import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function NavBar() {
  const { isAuthenticated, user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <nav className="navbar">
      <div className="nav-left">
        <NavLink to="/" className="brand" end>
          🎬 CinemaBox
        </NavLink>
        <NavLink
          to="/"
          end
          className={({ isActive }) => (isActive ? "active" : "")}
        >
          Trang chủ
        </NavLink>
        {isAuthenticated && (
          <NavLink
            to="/bookings"
            className={({ isActive }) => (isActive ? "active" : "")}
          >
            Đơn của tôi
          </NavLink>
        )}
      </div>
      <div className="nav-right">
        {isAuthenticated ? (
          <>
            <span className="user-email">{user?.email}</span>
            <button
              type="button"
              onClick={handleLogout}
              className="btn btn-ghost"
            >
              Đăng xuất
            </button>
          </>
        ) : (
          <NavLink to="/login" className="btn btn-primary">
            Đăng nhập
          </NavLink>
        )}
      </div>
    </nav>
  );
}
