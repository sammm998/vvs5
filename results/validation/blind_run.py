"""BLIND PASS. Push every reference drawing through the running system exactly as a user would - register,
create a project, upload the PDF, run the analysis, read the quantities back off the API - and write down what
came out. This script must never read a facit; scoring is a separate step that runs afterwards.

    python results/validation/blind_run.py /tmp/gate.json        # every reference drawing
    python results/validation/metrics.py  /tmp/gate.json        # ...and what it was worth

The two halves are separate on purpose. This one can see the drawings and never the answers; the scorer can see
the answers and never invokes the engine. Nothing a facit says can reach a measurement.
"""
import json, os, sys, tempfile, time

ROOT = os.environ.get("VVS_ROOT", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
OUT = sys.argv[1]


def _pdf(tag):
    """The drawing a tag names, in either half of the reference set."""
    a = f"{ROOT}/data/validation_{tag}/clean.pdf"
    return a if os.path.exists(a) else f"{ROOT}/data/validation_set3/{tag}/clean.pdf"


def _all_tags():
    out = [t for t in ("A", "C", "D", "E") if os.path.exists(f"{ROOT}/data/validation_{t}/clean.pdf")]
    d = f"{ROOT}/data/validation_set3"
    if os.path.isdir(d):
        out += sorted(n for n in os.listdir(d) if os.path.exists(f"{d}/{n}/clean.pdf"))
    return out


TAGS = sys.argv[2:] or _all_tags()

tmp = tempfile.mkdtemp(prefix="blind-")
os.environ["VVS_DATABASE_URL"] = f"sqlite:///{tmp}/blind.db"
os.environ["VVS_STORAGE_ROOT"] = f"{tmp}/storage"
os.environ["VVS_SECRET_KEY"] = "blind"
sys.path.insert(0, os.path.join(ROOT, "backend"))
sys.path.insert(0, os.path.join(ROOT, "engine"))

from fastapi.testclient import TestClient
from app.main import app

records = {}
with TestClient(app) as c:
    assert c.get("/health").json()["status"] == "ok"
    tok = c.post("/api/auth/register", json={"email": "blind@example.com", "password": "hemligt1"}).json()["access_token"]
    H = {"Authorization": f"Bearer {tok}"}
    for tag in TAGS:
        # one project per drawing: A, C, D and E are four different buildings, and a reading that let one teach
        # another would not be the blind reading of a single sheet that this gate measures
        proj = c.post("/api/projects", json={"name": f"Blind {tag}", "description": ""}, headers=H).json()
        pdf = _pdf(tag)
        t0 = time.time()
        with open(pdf, "rb") as fh:
            d = c.post(f"/api/projects/{proj['id']}/drawings",
                       files={"file": (f"{tag}.pdf", fh, "application/pdf")}, headers=H).json()
        j = c.post(f"/api/drawings/{d['id']}/analyze", headers=H).json()
        for _ in range(1200):
            j = c.get(f"/api/jobs/{j['id']}", headers=H).json()
            if j["status"] in ("COMPLETED", "FAILED"):
                break
            time.sleep(0.5)
        if j["status"] != "COMPLETED":
            records[tag] = {"state": "FAILED", "error": (j.get("error") or "")[:400]}
            print(f"{tag}: FAILED", flush=True)
            continue
        res = c.get(f"/api/jobs/{j['id']}/result", headers=H).json()
        exports = {}
        for fmt in ("xlsx", "csv", "json", "report", "pdf"):
            exports[fmt] = c.get(f"/api/jobs/{j['id']}/export/{fmt}", headers=H).status_code
        arts = sorted(a["name"] for a in c.get(f"/api/jobs/{j['id']}/artifacts", headers=H).json())
        records[tag] = {
            "state": "OK",
            "seconds": round(time.time() - t0, 1),
            "n_pages": d["n_pages"],
            "scale": {"state": res["scale"]["state"], "reason": res["scale"].get("reason"),
                      "meters_per_pt": res["scale"].get("meters_per_pt")},
            "coverage": res["coverage"],
            "quantities": [{k: q.get(k) for k in
                            ("designation", "base", "dn", "state", "label_count", "physical_pipe_count",
                             "confirmed_horizontal_m", "confirmed_total_m", "confirmed_vertical_m", "horizontal_calc", "vertical_calc", "total_calc",
                             "ambiguous_m", "in_hatched_area_m", "risers_calc", "riser_count",
                             "riser_count_from_labels")}
                           for q in sorted(res["quantities"], key=lambda q: q["designation"])],
            "totals": res["totals"],
            "n_issues": len(res["issues"]),
            "issues_by_kind": {k: sum(1 for i in res["issues"] if i["kind"] == k)
                               for k in sorted({i["kind"] for i in res["issues"]})},
            "blocking": sum(1 for i in res["issues"] if i.get("severity") == "blocking"),
            "advisory": sum(1 for i in res["issues"] if i.get("severity") == "advisory"),
            "ambiguous_geometry": len(res["ambiguous_geometry"]),
            "unowned_geometry": len(res["unowned_geometry"]),
            "exports": exports,
            "artifacts": arts,
        }
        q = records[tag]["quantities"]
        print(f"{tag}: OK {records[tag]['seconds']}s  skala {res['scale']['state']}  "
              f"{len(q)} beteckningar {sorted(x[chr(39)+chr(39)] if False else x['designation'] for x in q)}  summa {sum(x['horizontal_calc'] or 0 for x in q):.2f} m", flush=True)

with open(OUT, "w") as fh:
    json.dump(records, fh, ensure_ascii=False, indent=1)
print("wrote", OUT)
