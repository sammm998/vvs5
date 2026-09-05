import { useState } from "react";
import { Link, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { getToken, setToken, currentEmail } from "./api";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Projects from "./pages/Projects";
import ProjectPage from "./pages/Project";
import DrawingPage from "./pages/Drawing";
import AnalysisPage from "./pages/Analysis";

function Guard({ children }: { children: JSX.Element }) {
  return getToken() ? children : <Navigate to="/login" replace />;
}

function Mark() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path d="M2 13h5V6h6v7h5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="square" />
    </svg>
  );
}

function IconProjects() {
  return (
    <svg width="17" height="17" viewBox="0 0 18 18" fill="none" aria-hidden="true">
      <rect x="2.5" y="4.5" width="10" height="11" stroke="currentColor" strokeWidth="1.3" />
      <path d="M5.5 2.5h10v11" stroke="currentColor" strokeWidth="1.3" />
    </svg>
  );
}

function IconRail() {
  return (
    <svg width="16" height="16" viewBox="0 0 18 18" fill="none" aria-hidden="true">
      <rect x="2.5" y="3.5" width="13" height="11" stroke="currentColor" strokeWidth="1.3" />
      <path d="M7 3.5v11" stroke="currentColor" strokeWidth="1.3" />
    </svg>
  );
}

function IconOut() {
  return (
    <svg width="15" height="15" viewBox="0 0 18 18" fill="none" aria-hidden="true">
      <path d="M11 3.5H4.5v11H11M8 9h7m0 0-2.5-2.5M15 9l-2.5 2.5" stroke="currentColor" strokeWidth="1.3" />
    </svg>
  );
}

const ROUTES = (
  <Routes>
    <Route path="/" element={<Landing />} />
    <Route path="/login" element={<Login />} />
    <Route path="/projekt" element={<Guard><Projects /></Guard>} />
    <Route path="/projects/:id" element={<Guard><ProjectPage /></Guard>} />
    <Route path="/drawings/:id" element={<Guard><DrawingPage /></Guard>} />
    <Route path="/jobs/:id" element={<Guard><AnalysisPage /></Guard>} />
  </Routes>
);

export default function App() {
  const nav = useNavigate();
  const { pathname } = useLocation();
  const [rail, setRail] = useState<boolean>(() => {
    try { return localStorage.getItem("vvs.rail") === "1"; } catch { return false; }
  });
  const toggleRail = () => setRail((v) => {
    try { localStorage.setItem("vvs.rail", v ? "0" : "1"); } catch { /* private window */ }
    return !v;
  });
  // the landing page and the login screen bring their own layout
  if (pathname === "/" || pathname === "/login") return ROUTES;
  const email = currentEmail();
  return (
    <div className={`app${rail ? " railed" : ""}`}>
      <aside className="side">
        <button className="ghost small railbtn" onClick={toggleRail}
          title={rail ? "Visa sidopanelen" : "Fäll ihop sidopanelen"}
          aria-label={rail ? "Visa sidopanelen" : "Fäll ihop sidopanelen"}><IconRail /></button>
        <div>
          <Link to="/projekt" className="brand"><Mark /> <span className="wide">VVS Mängdning</span></Link>
          <div className="org wide" style={{ marginTop: 10 }}>Mängdning ur ren vektor</div>
        </div>
        <nav>
          <Link to="/projekt" className={pathname.startsWith("/projekt") || pathname.startsWith("/projects") ? "on" : ""}>
            <IconProjects /> <span className="wide">Projekt</span>
          </Link>
        </nav>
        <div className="foot">
          {email && <div className="who wide">{email}</div>}
          <button className="secondary small" style={{ alignSelf: "flex-start", display: "inline-flex", alignItems: "center", gap: 8 }}
            onClick={() => { setToken(null); nav("/"); }}>
            <IconOut /> <span className="wide">Logga ut</span>
          </button>
        </div>
      </aside>
      <div className="main">{ROUTES}</div>
    </div>
  );
}
