import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

export default function Projects() {
  const [projects, setProjects] = useState<any[]>([]);
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [err, setErr] = useState("");
  const load = () => api.projects().then(setProjects).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, []);
  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    try { await api.createProject(name, desc); setName(""); setDesc(""); load(); } catch (ex: any) { setErr(ex.message); }
  };
  return (
    <main>
      <h2>Projekt</h2>
      <form className="card row" onSubmit={create}>
        <input placeholder="Projektnamn" value={name} onChange={(e) => setName(e.target.value)} required />
        <input placeholder="Beskrivning" value={desc} onChange={(e) => setDesc(e.target.value)} />
        <button type="submit">Skapa projekt</button>
      </form>
      {err && <p className="error">{err}</p>}
      <div className="card">
        <table>
          <thead><tr><th>Namn</th><th>Beskrivning</th><th>Ritningar</th><th>Skapad</th><th></th></tr></thead>
          <tbody>
            {projects.map((p) => (
              <tr key={p.id}>
                <td><Link to={`/projects/${p.id}`}>{p.name}</Link></td><td>{p.description}</td><td>{p.n_drawings}</td>
                <td className="muted">{new Date(p.created_at).toLocaleString("sv-SE")}</td>
                <td><button className="secondary small" onClick={async () => { if (confirm("Ta bort projektet?")) { await api.deleteProject(p.id); load(); } }}>Ta bort</button></td>
              </tr>
            ))}
            {projects.length === 0 && <tr><td colSpan={5} className="muted">Inga projekt ännu.</td></tr>}
          </tbody>
        </table>
      </div>
    </main>
  );
}
