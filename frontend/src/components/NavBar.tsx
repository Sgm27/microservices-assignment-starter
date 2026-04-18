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
          Home
        </NavLink>
        {isAuthenticated && (
          <NavLink
            to="/bookings"
            className={({ isActive }) => (isActive ? "active" : "")}
          >
            My Bookings
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
              Logout
            </button>
          </>
        ) : (
          <NavLink to="/login" className="btn btn-primary">
            Login
          </NavLink>
        )}
      </div>
    </nav>
  );
}
