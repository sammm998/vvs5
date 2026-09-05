import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";

/* The same run as on the front page, drawn small: a labelled pipe and one the drawing does not name. */
function Motif() {
  return (
    <svg viewBox="0 0 470 190" role="img" aria-label="Rör markerade och mätta ur en ritning">
      <g stroke="#2f343d" strokeWidth="1.2" fill="none">
        <path d="M20 24 H300 V166 H20 Z M160 24 V166 M20 100 H160" />
      </g>
      <g fill="none" strokeWidth="2.8" strokeLinecap="butt">
        <path d="M46 138 H210 V70 H330" stroke="#6ee7a5" strokeOpacity="0.9" strokeDasharray="14 5 2.5 5" />
        <path d="M210 138 H286" stroke="#60a5fa" strokeOpacity="0.85" strokeDasharray="14 5 2.5 5" />
        <path d="M348 132 H438" stroke="#4b5160" strokeDasharray="14 5 2.5 5" />
      </g>
      <g fill="#0a0b0d" strokeWidth="1.8">
        <circle cx="46" cy="138" r="4" stroke="#6ee7a5" />
        <circle cx="330" cy="70" r="4" stroke="#6ee7a5" />
        <circle cx="286" cy="138" r="4" stroke="#60a5fa" />
      </g>
      <g fontFamily="ui-monospace, SFMono-Regular, monospace">
        <path d="M414 62 H344 L332 70" stroke="#6ee7a5" strokeOpacity="0.45" strokeWidth="1" fill="none" />
        <text x="344" y="40" fill="#f0f2f5" fontSize="12.5">S1-P5-110</text>
        <text x="344" y="56" fill="#8b929e" fontSize="11.5">24,8 m</text>
        <text x="348" y="122" fill="#5b616c" fontSize="11.5">onämnd</text>
      </g>
    </svg>
  );
}

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"login" | "register">("login");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      if (mode === "login") await api.login(email, password);
      else await api.register(email, password);
      nav("/projekt");
    } catch (ex: any) {
      setErr(ex.message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="auth">
      <div className="auth-form">
        <form onSubmit={submit}>
          <h1>{mode === "login" ? "Logga in" : "Skapa konto"}</h1>
          <p className="sub">
            {mode === "login"
              ? "Ladda upp en VVS-ritning och få mängden med beläggen kvar."
              : "Ett konto räcker för att köra en första ritning och jämföra mot din egen handmängdning."}
          </p>

          <div className="field">
            <label htmlFor="lg-email">E-post</label>
            <input
              id="lg-email"
              placeholder="namn@foretag.se"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="lg-pw">Lösenord</label>
            <input
              id="lg-pw"
              placeholder="••••••••"
              type="password"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          {err && <p className="error">{err}</p>}

          <button type="submit" disabled={busy}>
            {busy ? "Ett ögonblick…" : mode === "login" ? "Logga in" : "Registrera"}
          </button>

          <p className="swap">
            {mode === "login" ? "Har du inget konto? " : "Har du redan ett konto? "}
            <button type="button" onClick={() => { setMode(mode === "login" ? "register" : "login"); setErr(""); }}>
              {mode === "login" ? "Skapa ett" : "Logga in"}
            </button>
          </p>
        </form>
      </div>

      <aside className="aside">
        <Motif />
        <blockquote>
          Tvetydigt är ett giltigt svar. Fel säkerhet är det inte.
        </blockquote>
        <div className="who">Principen hela motorn är byggd kring</div>
        <div className="facts">
          <div>
            <b>15,6 m</b>
            samlad avvikelse mot facit,
            <br />
            fyra referensritningar
          </div>
          <div>
            <b>215</b>
            sidor i stilbiblioteket,
            <br />
            körda vid varje ändring
          </div>
          <div>
            <b>0</b>
            gissningar — identitet
            <br />
            endast via ledarlinjer
          </div>
        </div>
      </aside>
    </div>
  );
}
