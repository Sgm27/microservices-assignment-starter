import { Link, useNavigate } from "react-router-dom";
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
        <Link to="/" className="brand">
          Cinema
        </Link>
        <Link to="/">Home</Link>
        {isAuthenticated && <Link to="/bookings">My Bookings</Link>}
      </div>
      <div className="nav-right">
        {isAuthenticated ? (
          <>
            <span className="user-email">{user?.email}</span>
            <button type="button" onClick={handleLogout} className="btn btn-ghost">
              Logout
            </button>
          </>
        ) : (
          <Link to="/login" className="btn btn-primary">
            Login
          </Link>
        )}
      </div>
    </nav>
  );
}
