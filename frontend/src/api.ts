const TOKEN_KEY = "vvs_token";
export function getToken(): string | null { return localStorage.getItem(TOKEN_KEY); }
export function setToken(t: string | null) { if (t) localStorage.setItem(TOKEN_KEY, t); else localStorage.removeItem(TOKEN_KEY); }

async function req(path: string, init: RequestInit = {}): Promise<any> {
  const headers: Record<string, string> = { ...(init.headers as any) };
  const tok = getToken();
  if (tok) headers["Authorization"] = `Bearer ${tok}`;
  const res = await fetch(path, { ...init, headers });
  if (res.status === 401) { setToken(null); window.location.href = "/login"; throw new Error("Ej inloggad"); }
  if (!res.ok) {
    let msg = res.statusText;
    try { const j = await res.json(); msg = j.detail || msg; } catch { /* ignore */ }
    throw new Error(msg);
  }
  const ct = res.headers.get("content-type") || "";
  return ct.includes("application/json") ? res.json() : res;
}

export const api = {
  login: async (email: string, password: string) => {
    const body = new URLSearchParams({ username: email, password });
    const res = await fetch("/api/auth/login", { method: "POST", body });
    if (!res.ok) throw new Error((await res.json()).detail || "Inloggning misslyckades");
    const j = await res.json(); setToken(j.access_token); return j;
  },
  register: async (email: string, password: string) => {
    const j = await req("/api/auth/register", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password }) });
    setToken(j.access_token); return j;
  },
  me: () => req("/api/auth/me"),
  projects: () => req("/api/projects"),
  createProject: (name: string, description: string) => req("/api/projects", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name, description }) }),
  project: (id: string) => req(`/api/projects/${id}`),
  deleteProject: (id: string) => req(`/api/projects/${id}`, { method: "DELETE" }),
  upload: (projectId: string, file: File) => { const fd = new FormData(); fd.append("file", file); return req(`/api/projects/${projectId}/drawings`, { method: "POST", body: fd }); },
  drawing: (id: string) => req(`/api/drawings/${id}`),
  deleteDrawing: (id: string) => req(`/api/drawings/${id}`, { method: "DELETE" }),
  analyze: (drawingId: string) => req(`/api/drawings/${drawingId}/analyze`, { method: "POST" }),
  job: (id: string) => req(`/api/jobs/${id}`),
  result: (id: string) => req(`/api/jobs/${id}/result`),
  artifacts: (id: string) => req(`/api/jobs/${id}/artifacts`),
  why: (jobId: string, pipeId: string) => req(`/api/jobs/${jobId}/why/${pipeId}`),
  fileUrl: (drawingId: string) => `/api/drawings/${drawingId}/file`,
  exportUrl: (jobId: string, fmt: string) => `/api/jobs/${jobId}/export/${fmt}`,
  artifactUrl: (jobId: string, name: string) => `/api/jobs/${jobId}/artifacts/${name}`,
  fetchBlob: async (path: string) => { const res = await fetch(path, { headers: { Authorization: `Bearer ${getToken()}` } }); if (!res.ok) throw new Error("Hämtning misslyckades"); return res.blob(); },
};
