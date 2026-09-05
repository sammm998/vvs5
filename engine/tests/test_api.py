import os
import sys
import time

import pytest


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("api")
    os.environ["VVS_DATABASE_URL"] = f"sqlite:///{tmp}/test.db"
    os.environ["VVS_STORAGE_ROOT"] = str(tmp / "storage")
    os.environ["VVS_SECRET_KEY"] = "test"
    backend = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
    sys.path.insert(0, os.path.abspath(backend))
    for m in list(sys.modules):
        if m.startswith("app"):
            del sys.modules[m]
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c


def test_full_api_workflow(client, synthetic_pdf):
    assert client.get("/health").json()["status"] == "ok"
    r = client.post("/api/auth/register", json={"email": "test@example.com", "password": "hemligt1"}); assert r.status_code == 200, r.text
    tok = r.json()["access_token"]; H = {"Authorization": f"Bearer {tok}"}
    assert client.get("/api/projects").status_code == 401
    p = client.post("/api/projects", json={"name": "Test", "description": "d"}, headers=H).json()
    with open(synthetic_pdf, "rb") as fh:
        d = client.post(f"/api/projects/{p['id']}/drawings", files={"file": ("synthetic.pdf", fh, "application/pdf")}, headers=H).json()
    assert d["n_pages"] == 1
    j = client.post(f"/api/drawings/{d['id']}/analyze", headers=H).json()
    for _ in range(120):
        j = client.get(f"/api/jobs/{j['id']}", headers=H).json()
        if j["status"] in ("COMPLETED", "FAILED"):
            break
        time.sleep(0.5)
    assert j["status"] == "COMPLETED", j
    res = client.get(f"/api/jobs/{j['id']}/result", headers=H).json()
    assert res["quantities"] and res["pipes"] and res["scale"]["state"] == "VERIFIED"
    assert res["coverage"]["reconciliation"] == "VALID"
    pid = res["pipes"][0]["physical_pipe_id"]
    why = client.get(f"/api/jobs/{j['id']}/why/{pid}", headers=H).json()
    assert why["evidence_chain"] and why["evidence_chain"][0]["leader"]["source_paths"]
    arts = client.get(f"/api/jobs/{j['id']}/artifacts", headers=H).json()
    assert {a["name"] for a in arts} >= {"quantities.json", "production-overlay.pdf", "freeze-manifest.json", "drawing-profile.json"}
    for fmt in ("xlsx", "csv", "json", "report", "pdf"):
        assert client.get(f"/api/jobs/{j['id']}/export/{fmt}", headers=H).status_code == 200
    # ownership isolation: another user cannot see the project
    r2 = client.post("/api/auth/register", json={"email": "other@example.com", "password": "hemligt1"}).json()
    assert client.get(f"/api/projects/{p['id']}", headers={"Authorization": f"Bearer {r2['access_token']}"}).status_code == 404


def test_a_correction_layers_over_the_reading_without_replacing_it(client, synthetic_pdf):
    """Through the API as a person would: read the sheet, correct it, see both figures, undo it."""
    r = client.post("/api/auth/register", json={"email": "korr@example.com", "password": "hemligt1"}).json()
    H = {"Authorization": f"Bearer {r['access_token']}"}
    p = client.post("/api/projects", json={"name": "Rättelser", "description": ""}, headers=H).json()
    with open(synthetic_pdf, "rb") as fh:
        d = client.post(f"/api/projects/{p['id']}/drawings",
                        files={"file": ("k.pdf", fh, "application/pdf")}, headers=H).json()
    j = client.post(f"/api/drawings/{d['id']}/analyze", headers=H).json()
    for _ in range(120):
        j = client.get(f"/api/jobs/{j['id']}", headers=H).json()
        if j["status"] in ("COMPLETED", "FAILED"):
            break
        time.sleep(0.5)
    assert j["status"] == "COMPLETED", j

    before = client.get(f"/api/jobs/{j['id']}/result", headers=H).json()
    assert before["corrections"] == [] and before["corrected_total_m"] is None
    name = before["quantities"][0]["designation"]
    engine_m = before["quantities"][0]["confirmed_total_m"]

    c = client.post(f"/api/drawings/{d['id']}/corrections", headers=H, json={
        "kind": "quantity", "designation": name, "job_id": j["id"],
        "payload": {"meters": engine_m + 5.0}, "note": "ritningen säger annat"}).json()
    assert c["id"] and c["undone"] is False

    after = client.get(f"/api/jobs/{j['id']}/result", headers=H).json()
    row = next(q for q in after["quantities"] if q["designation"] == name)
    assert row["confirmed_total_m"] == engine_m + 5.0
    assert row["engine_total_m"] == engine_m, "the engine's own reading has to stay visible beside the correction"
    assert after["corrections_applied"][0]["applied"] is True

    client.delete(f"/api/drawings/{d['id']}/corrections/{c['id']}", headers=H)
    undone = client.get(f"/api/jobs/{j['id']}/result", headers=H).json()
    assert next(q for q in undone["quantities"] if q["designation"] == name)["confirmed_total_m"] == engine_m

    # an unknown kind is refused rather than stored as something the layer would then ignore
    assert client.post(f"/api/drawings/{d['id']}/corrections", headers=H,
                       json={"kind": "hitta-på", "designation": name}).status_code == 400
    # and another account cannot see or add corrections on this drawing
    other = client.post("/api/auth/register", json={"email": "annan@example.com", "password": "hemligt1"}).json()
    OH = {"Authorization": f"Bearer {other['access_token']}"}
    assert client.get(f"/api/drawings/{d['id']}/corrections", headers=OH).status_code == 404
