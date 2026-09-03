import { Link, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { getToken, setToken } from "./api";
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
  return (
    <>
      <header className="top">
        <Link to="/" className="brand">VVS Mängdning</Link>
        <Link to="/">Projekt</Link>
        <span className="spacer" />
        {getToken() && <button className="secondary small" onClick={() => { setToken(null); nav("/login"); }}>Logga ut</button>}
      </header>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<Guard><Projects /></Guard>} />
        <Route path="/projects/:id" element={<Guard><ProjectPage /></Guard>} />
        <Route path="/drawings/:id" element={<Guard><DrawingPage /></Guard>} />
        <Route path="/jobs/:id" element={<Guard><AnalysisPage /></Guard>} />
      </Routes>
    </>
  );
}
