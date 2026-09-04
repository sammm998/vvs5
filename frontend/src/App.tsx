import { Link, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { getToken, setToken } from "./api";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Projects from "./pages/Projects";
import ProjectPage from "./pages/Project";
import DrawingPage from "./pages/Drawing";
import AnalysisPage from "./pages/Analysis";

function Guard({ children }: { children: JSX.Element }) {
  return getToken() ? children : <Navigate to="/login" replace />;
}

export default function App() {
  const nav = useNavigate();
  const { pathname } = useLocation();
  const bare = pathname === "/";      // the landing page brings its own navigation
  return (
    <>
      {!bare && (
        <header className="top">
          <Link to="/" className="brand">VVS Mängdning</Link>
          <Link to="/projekt">Projekt</Link>
          <span className="spacer" />
          {getToken() && <button className="secondary small" onClick={() => { setToken(null); nav("/"); }}>Logga ut</button>}
        </header>
      )}
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/projekt" element={<Guard><Projects /></Guard>} />
        <Route path="/projects/:id" element={<Guard><ProjectPage /></Guard>} />
        <Route path="/drawings/:id" element={<Guard><DrawingPage /></Guard>} />
        <Route path="/jobs/:id" element={<Guard><AnalysisPage /></Guard>} />
      </Routes>
    </>
  );
}
