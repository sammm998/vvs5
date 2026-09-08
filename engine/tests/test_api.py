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


def test_a_correction_is_filed_with_the_situation_the_reading_actually_saw(client, synthetic_pdf):
    """The server, not the browser, says what case a correction was made in - and it has to say something.

    A situation that comes back empty is not a harmless default: `lessons()` drops every correction that has
    one, so an empty fingerprint silently switches the whole learning loop off. This asserts the server reads a
    real one off its own artifacts, and that a fingerprint invented by a caller is refused rather than stored.
    """
    r = client.post("/api/auth/register", json={"email": "sit@example.com", "password": "hemligt1"}).json()
    H = {"Authorization": f"Bearer {r['access_token']}"}
    p = client.post("/api/projects", json={"name": "Situation", "description": ""}, headers=H).json()
    with open(synthetic_pdf, "rb") as fh:
        d = client.post(f"/api/projects/{p['id']}/drawings",
                        files={"file": ("s.pdf", fh, "application/pdf")}, headers=H).json()
    j = client.post(f"/api/drawings/{d['id']}/analyze", headers=H).json()
    for _ in range(120):
        j = client.get(f"/api/jobs/{j['id']}", headers=H).json()
        if j["status"] in ("COMPLETED", "FAILED"):
            break
        time.sleep(0.5)
    assert j["status"] == "COMPLETED", j
    res = client.get(f"/api/jobs/{j['id']}/result", headers=H).json()

    # a designation the reading left unresolved, if this sheet has one: that is where a situation exists at all
    open_names = {(a.get("designation") or "") for a in res["anchors"]
                  if a["state"] != "VERIFIED_PIPE_ATTACHMENT"}
    forged = {"family_style": "w9.99|c(1,1,1)", "leader_style": "påhittad", "reason": "påhittad",
              "designation_shape": "AA9-A99-99", "topology": "1-1-1", "candidate_shape": "1:AA9-A99-99"}
    name = sorted(open_names)[0] if open_names else res["quantities"][0]["designation"]
    c = client.post(f"/api/drawings/{d['id']}/corrections", headers=H, json={
        "kind": "retag", "designation": name, "job_id": j["id"],
        "payload": {"from": name, "meters": 1.0}, "situation": forged}).json()
    stored = next(x for x in client.get(f"/api/drawings/{d['id']}/corrections", headers=H).json()
                  if x["id"] == c["id"])["situation"]
    assert stored != forged, "a fingerprint the caller made up must never be stored as if the reading saw it"
    if open_names:
        assert stored.get("family_style") or stored.get("reason"), \
            "the reading had an unresolved case for this designation, so the server owed it a real situation"


def test_an_export_carries_the_corrected_reading_and_the_riser_source_on_screen(client, synthetic_pdf):
    """A file someone prices from must not disagree with the screen it was taken from.

    Two ways it used to: the export read the engine's own artifact and dropped every correction, and it counted
    drawn riser symbols while the table counted labelled ones, so the assumed vertical metres differed too.
    """
    import csv as _csv
    import io as _io
    r = client.post("/api/auth/register", json={"email": "exp@example.com", "password": "hemligt1"}).json()
    H = {"Authorization": f"Bearer {r['access_token']}"}
    p = client.post("/api/projects", json={"name": "Export", "description": ""}, headers=H).json()
    with open(synthetic_pdf, "rb") as fh:
        d = client.post(f"/api/projects/{p['id']}/drawings",
                        files={"file": ("e.pdf", fh, "application/pdf")}, headers=H).json()
    j = client.post(f"/api/drawings/{d['id']}/analyze", headers=H).json()
    for _ in range(120):
        j = client.get(f"/api/jobs/{j['id']}", headers=H).json()
        if j["status"] in ("COMPLETED", "FAILED"):
            break
        time.sleep(0.5)
    assert j["status"] == "COMPLETED", j
    res = client.get(f"/api/jobs/{j['id']}/result", headers=H).json()
    name = res["quantities"][0]["designation"]
    engine_m = res["quantities"][0]["confirmed_total_m"]

    client.post(f"/api/drawings/{d['id']}/corrections", headers=H, json={
        "kind": "quantity", "designation": name, "job_id": j["id"],
        "payload": {"meters": engine_m + 7.0}, "note": "rättad för hand"})

    def row_of(text):
        rows = list(_csv.reader(_io.StringIO(text), delimiter=";"))
        head = rows[0]
        return dict(zip(head, next(r for r in rows[1:] if r and r[0] == name)))

    got = row_of(client.get(f"/api/jobs/{j['id']}/export/csv", headers=H).content.decode("utf-8-sig"))
    assert float(got["Totalt m"].replace(",", ".")) == round(engine_m + 7.0, 2), \
        "the export handed back the engine's figure, not the one the reader corrected it to"
    assert "Vertikalt ursprung" in got

    # the two riser sources are counted separately, and the export must count the one it was asked for
    q = next(x for x in res["quantities"] if x["designation"] == name)
    for src in ("labels", "symbols"):
        n = q["riser_count_from_labels"] if src == "labels" else q["riser_count"]
        got = row_of(client.get(f"/api/jobs/{j['id']}/export/csv?floor_height=2.8&riser_source={src}",
                                headers=H).content.decode("utf-8-sig"))
        if n:
            assert f"{n} stigare" in got["Vertikalt ursprung"], (src, n, got["Vertikalt ursprung"])
        else:
            assert "ANTAGET" not in got["Vertikalt ursprung"]


def test_an_agent_proposal_is_only_written_when_a_person_accepts_it(client, synthetic_pdf):
    """The agent proposes; accepting writes. And what is written is what the server recomputes, not what it is sent."""
    r = client.post("/api/auth/register", json={"email": "forslag@example.com", "password": "hemligt1"}).json()
    H = {"Authorization": f"Bearer {r['access_token']}"}
    p = client.post("/api/projects", json={"name": "Förslag", "description": ""}, headers=H).json()
    with open(synthetic_pdf, "rb") as fh:
        d = client.post(f"/api/projects/{p['id']}/drawings",
                        files={"file": ("f.pdf", fh, "application/pdf")}, headers=H).json()
    j = client.post(f"/api/drawings/{d['id']}/analyze", headers=H).json()
    for _ in range(120):
        j = client.get(f"/api/jobs/{j['id']}", headers=H).json()
        if j["status"] in ("COMPLETED", "FAILED"):
            break
        time.sleep(0.5)
    assert j["status"] == "COMPLETED", j

    before = client.get(f"/api/jobs/{j['id']}/result", headers=H).json()
    pipe = next(x for x in before["pipes"] if x.get("designation") and (x.get("horizontal_m") or 0) > 0)
    name, metres = pipe["designation"], pipe["horizontal_m"]
    row_before = next(q for q in before["quantities"] if q["designation"] == name)["confirmed_total_m"]

    # asking is not changing: running the tool leaves the reading exactly as it was
    args = {"ror_id": [pipe["physical_pipe_id"]], "skal": "ligger i vägg"}
    proposal = client.post(f"/api/jobs/{j['id']}/agent/tool", headers=H,
                           json={"name": "foresla_radera_ror", "arguments": args}).json()
    assert proposal["verktyg"][0]["resultat"]["tillstand"] == "FORESLAGEN"
    assert client.get(f"/api/jobs/{j['id']}/result", headers=H).json()["corrections"] == []

    # accepting writes it, and the metres are the reading's own
    out = client.post(f"/api/jobs/{j['id']}/agent/edit", headers=H,
                      json={"name": "foresla_radera_ror", "arguments": args, "note": "godkänt"}).json()
    assert len(out["skrivna"]) == 1 and abs(out["berord_meter"] - metres) < 0.01
    after = client.get(f"/api/jobs/{j['id']}/result", headers=H).json()
    row_after = next(q for q in after["quantities"] if q["designation"] == name)
    assert abs(row_after["confirmed_total_m"] - (row_before - metres)) < 0.01
    assert row_after["engine_total_m"] == row_before, "the engine's own figure has to survive the correction"

    # and it can be undone like any other correction
    client.delete(f"/api/drawings/{d['id']}/corrections/{out['skrivna'][0]['id']}", headers=H)
    undone = client.get(f"/api/jobs/{j['id']}/result", headers=H).json()
    assert next(q for q in undone["quantities"] if q["designation"] == name)["confirmed_total_m"] == row_before

    # a reading tool cannot be pushed through the change path, and a refused proposal writes nothing
    assert client.post(f"/api/jobs/{j['id']}/agent/edit", headers=H,
                       json={"name": "mangda", "arguments": {}}).status_code == 400
    assert client.post(f"/api/jobs/{j['id']}/agent/edit", headers=H,
                       json={"name": "foresla_byt_beteckning",
                             "arguments": {"ror_id": [pipe["physical_pipe_id"]],
                                           "till_beteckning": "PÅHITT-1-999"}}).status_code == 409
    assert client.get(f"/api/drawings/{d['id']}/corrections", headers=H).json()[0]["undone"] is True
