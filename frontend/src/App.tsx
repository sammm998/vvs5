import { useState } from "react";
import { Link, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { getToken, setToken, currentEmail } from "./api";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Docs from "./pages/Docs";
import Projects from "./pages/Projects";
import ProjectPage from "./pages/Project";
import DrawingPage from "./pages/Drawing";
import AnalysisPage from "./pages/Analysis";
import Boundary from "./components/Boundary";
import LearnPage from "./pages/LearnPage";
import SettingsPage from "./pages/Settings";

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

function IconRules() {
  return (
    <svg width="17" height="17" viewBox="0 0 18 18" fill="none" aria-hidden="true">
      <circle cx="9" cy="9" r="2.4" stroke="currentColor" strokeWidth="1.3" />
      <path d="M9 1.6v2.2M9 14.2v2.2M1.6 9h2.2M14.2 9h2.2M3.8 3.8l1.6 1.6M12.6 12.6l1.6 1.6M14.2 3.8l-1.6 1.6M5.4 12.6l-1.6 1.6"
        stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  );
}

function IconLearn() {
  return (
    <svg width="17" height="17" viewBox="0 0 18 18" fill="none" aria-hidden="true">
      <path d="M2.5 5.2 9 2.5l6.5 2.7L9 8 2.5 5.2Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
      <path d="M5 6.7v4.1c0 1.2 1.8 2.2 4 2.2s4-1 4-2.2V6.7" stroke="currentColor" strokeWidth="1.3" />
      <path d="M15.5 5.4v4.2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
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
  <Boundary what="sidan">
  <Routes>
    <Route path="/" element={<Landing />} />
    <Route path="/login" element={<Login />} />
    <Route path="/dokumentation" element={<Docs />} />
    <Route path="/projekt" element={<Guard><Projects /></Guard>} />
    <Route path="/projects/:id" element={<Guard><ProjectPage /></Guard>} />
    <Route path="/drawings/:id" element={<Guard><DrawingPage /></Guard>} />
    <Route path="/jobs/:id" element={<Guard><AnalysisPage /></Guard>} />
    <Route path="/lar" element={<Guard><LearnPage /></Guard>} />
    <Route path="/installningar" element={<Guard><SettingsPage /></Guard>} />
  </Routes>
  </Boundary>
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
  // a trailing slash is the same page: without this, /dokumentation/ fell through and got the app's sidebar
  const path = pathname.length > 1 ? pathname.replace(/\/+$/, "") : pathname;
  if (path === "" || path === "/" || path === "/login" || path === "/dokumentation") return ROUTES;
  const email = currentEmail();
  // On a reading, the drawing is the page. The sidebar carries one link and a sign-out; on a wide sheet those
  // 244 px are the difference between seeing the whole drawing and hunting across it, so this route opens with
  // the sidebar folded to its rail. It is still one click away, and a reader who unfolds it keeps it unfolded.
  const chosen = (() => { try { return localStorage.getItem("vvs.rail") !== null; } catch { return false; } })();
  const railed = rail || (!chosen && path.startsWith("/jobs/"));
  return (
    <div className={`app${railed ? " railed" : ""}`}>
      <aside className="side">
        <button className="ghost small railbtn" onClick={toggleRail}
          title={rail ? "Visa sidopanelen" : "Fäll ihop sidopanelen"}
          aria-label={rail ? "Visa sidopanelen" : "Fäll ihop sidopanelen"}><IconRail /></button>
        <div>
          <Link to="/projekt" className="brand"><Mark /> <span className="wide">VVS Mängdning</span></Link>
          <div className="org wide" style={{ marginTop: 10 }}>Mängdning ur ren vektor</div>
        </div>
        <nav>
          <Link to="/projekt" className={path.startsWith("/projekt") || path.startsWith("/projects") ? "on" : ""}>
            <IconProjects /> <span className="wide">Projekt</span>
          </Link>
          <Link to="/lar" className={path.startsWith("/lar") ? "on" : ""}>
            <IconLearn /> <span className="wide">Lär dig VVS</span>
          </Link>
          <Link to="/installningar" className={path.startsWith("/installningar") ? "on" : ""}>
            <IconRules /> <span className="wide">Inställningar</span>
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
