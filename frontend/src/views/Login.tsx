import { useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { login, register } from "../api/auth";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { login: doLogin } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const auth =
        mode === "login"
          ? await login({ email, password })
          : await register({
              email,
              password,
              full_name: fullName,
              phone: phone || undefined,
            });
      doLogin(auth);
      navigate("/");
    } catch (err) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Đăng nhập thất bại";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card narrow">
      <h1>{mode === "login" ? "Đăng nhập" : "Tạo tài khoản"}</h1>
      <form onSubmit={handleSubmit} className="form">
        <label>
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </label>
        <label>
          Mật khẩu
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
          />
        </label>
        {mode === "register" && (
          <>
            <label>
              Họ tên
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
              />
            </label>
            <label>
              Số điện thoại (tùy chọn)
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
              />
            </label>
          </>
        )}
        {error && <p className="error">{error}</p>}
        <button type="submit" className="btn btn-primary" disabled={loading}>
          {loading
            ? "Đang xử lý…"
            : mode === "login"
              ? "Đăng nhập"
              : "Đăng ký"}
        </button>
      </form>
      <p className="muted">
        {mode === "login" ? "Chưa có tài khoản?" : "Đã có tài khoản?"}{" "}
        <button
          type="button"
          className="btn btn-link"
          onClick={() => setMode(mode === "login" ? "register" : "login")}
        >
          {mode === "login" ? "Đăng ký" : "Đăng nhập"}
        </button>
      </p>
    </div>
  );
}
