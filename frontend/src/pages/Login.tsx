import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"login" | "register">("login");
  const [err, setErr] = useState("");
  const nav = useNavigate();
  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setErr("");
    try { if (mode === "login") await api.login(email, password); else await api.register(email, password); nav("/projekt"); }
    catch (ex: any) { setErr(ex.message); }
  };
  return (
    <main>
      <form className="card login" onSubmit={submit}>
        <h2>{mode === "login" ? "Logga in" : "Skapa konto"}</h2>
        <input placeholder="E-post" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <input placeholder="Lösenord" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        {err && <p className="error">{err}</p>}
        <div className="row">
          <button type="submit">{mode === "login" ? "Logga in" : "Registrera"}</button>
          <button type="button" className="secondary" onClick={() => setMode(mode === "login" ? "register" : "login")}>
            {mode === "login" ? "Skapa konto" : "Har redan konto"}
          </button>
        </div>
      </form>
    </main>
  );
}
