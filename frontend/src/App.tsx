import { HashRouter } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import NavBar from "./components/NavBar";
import AppRoutes from "./router";

export default function App() {
  return (
    <HashRouter>
      <AuthProvider>
        <div className="app-shell">
          <NavBar />
          <main className="container">
            <AppRoutes />
          </main>
        </div>
      </AuthProvider>
    </HashRouter>
  );
}
