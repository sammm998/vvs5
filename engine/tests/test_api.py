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


def test_rules_are_open_and_movable(client):
    """Reglerna ska gå att läsa, flytta och sätta tillbaka - och vägra det som inte betyder något."""
    tok = client.post("/api/auth/register", json={"email": "regler@example.com", "password": "hemligt1"}).json()["access_token"]
    H = {"Authorization": f"Bearer {tok}"}

    cat = client.get("/api/rules", headers=H).json()
    assert cat["n_rules"] > 30 and cat["n_tunable"] > 20
    ids = {r["id"] for g in cat["groups"] for r in g["rules"]}
    assert "semantics.attachment.NEAR_MISS" in ids
    assert all(r["title"] and r["why"] for g in cat["groups"] for r in g["rules"])

    rid = "semantics.attachment.NEAR_MISS"
    assert client.put(f"/api/rules/{rid}", json={"value": 9.5, "note": "kort ledare"}, headers=H).status_code == 200
    row = next(r for g in client.get("/api/rules", headers=H).json()["groups"] for r in g["rules"] if r["id"] == rid)
    assert row["value"] == 9.5 and row["changed"] and row["note"] == "kort ledare"

    # utanför vad regeln kan betyda, en regel som inte får flyttas, och en som inte finns
    assert client.put(f"/api/rules/{rid}", json={"value": 10_000}, headers=H).status_code == 400
    assert client.put("/api/rules/semantics.leaders.TOUCH_TOL", json={"value": 1.0}, headers=H).status_code == 400
    assert client.put("/api/rules/inte.en.regel", json={"value": 1}, headers=H).status_code == 404

    assert client.put(f"/api/rules/{rid}", json={"reset": True}, headers=H).status_code == 200
    assert client.get("/api/rules", headers=H).json()["n_changed"] == 0


def test_one_readers_rules_do_not_reach_another(client):
    """Ett konto som flyttat en regel får inte flytta den för någon annan."""
    a = client.post("/api/auth/register", json={"email": "a@example.com", "password": "hemligt1"}).json()["access_token"]
    b = client.post("/api/auth/register", json={"email": "b@example.com", "password": "hemligt1"}).json()["access_token"]
    rid = "semantics.attachment.NEAR_MISS"
    client.put(f"/api/rules/{rid}", json={"value": 11.0}, headers={"Authorization": f"Bearer {a}"})
    mine = next(r for g in client.get("/api/rules", headers={"Authorization": f"Bearer {a}"}).json()["groups"]
                for r in g["rules"] if r["id"] == rid)
    theirs = next(r for g in client.get("/api/rules", headers={"Authorization": f"Bearer {b}"}).json()["groups"]
                  for r in g["rules"] if r["id"] == rid)
    assert mine["value"] == 11.0 and mine["changed"]
    assert theirs["value"] == theirs["default"] and not theirs["changed"]


# ----------------------------------------------------------------------------------------------------------
# projektanalysen: hela handlingen läst som en modell
# ----------------------------------------------------------------------------------------------------------

def _titled(path, lines):
    """Ett blad med en namnruta, nere till höger där svenska ritningar bär den."""
    import pymupdf
    d = pymupdf.open()
    pg = d.new_page(width=842, height=595)
    y = 0.62 * 595
    for t in lines:
        pg.insert_text((0.60 * 842, y), t, fontsize=9, fontname="helv")
        y += 13
    d.save(path); d.close()
    return path


def test_a_project_is_read_as_one_handling_and_never_invents_a_before_and_after(client, tmp_path):
    """Genom API:t som en människa gör det: välj läge, läs handlingen, se vad den består av.

    Det som prövas här är inte att siffrorna blir rätt utan att påståendena är sanna. Tre blad i två hus är
    två hus. Två blad från samma dag i samma skede är inte ett revisionspar - de ska stå som oklara med vad
    de verkar vara, för en påhittad diff ser exakt ut som en riktig och varje rad i den är fel.
    """
    r = client.post("/api/auth/register", json={"email": "handling@example.com", "password": "hemligt1"}).json()
    H = {"Authorization": f"Bearer {r['access_token']}"}
    p = client.post("/api/projects", json={"name": "Toftaskolan", "description": ""}, headers=H).json()

    # ett projekt utan valt läge är ett av de gamla: det svarar "simple" utan att skriva något
    m = client.get(f"/api/projects/{p['id']}/mode", headers=H).json()
    assert m["chosen"] is False and m["effective"] == "simple"

    sheets = {
        "V-50-1-A0111.pdf": ["V-50-1-A0111", "HUS A, PLAN 1, RORINSTALLATIONER", "BYGGHANDLING", "2024-05-07"],
        "V-50-1-B0112.pdf": ["V-50-1-B0112", "HUS B, PLAN 1, RORINSTALLATIONER", "BYGGHANDLING", "2024-05-07"],
        # samma nummer, samma dag, samma skede: två filer utan någon ordning i sig
        "V-50-1-A0113 (1).pdf": ["V-50-1-A0113", "HUS A, PLAN 2, RORINSTALLATIONER", "BYGGHANDLING", "2024-05-07"],
        "V-50-1-A0113 (2).pdf": ["V-50-1-A0113", "HUS A, PLAN 2, RORINSTALLATIONER", "BYGGHANDLING", "2024-05-07"],
    }
    ids = {}
    for name, lines in sheets.items():
        f = _titled(str(tmp_path / name), lines)
        with open(f, "rb") as fh:
            d = client.post(f"/api/projects/{p['id']}/drawings",
                            files={"file": (name, fh, "application/pdf")}, headers=H).json()
        ids[name] = d["id"]

    assert client.put(f"/api/projects/{p['id']}/mode", json={"mode": "projekt"}, headers=H).status_code == 400
    assert client.put(f"/api/projects/{p['id']}/mode", json={"mode": "project"}, headers=H).status_code == 200

    rep = _run_handling(client, H, p["id"])
    assert rep["totals"]["documents"] == 4
    assert rep["buildings"] == ["A", "B"], rep["buildings"]
    assert rep["disciplines"] == ["VVS"], rep["disciplines"]
    assert rep["totals"]["pairs"] == 0, "ett tal i filnamnet är ingen revision"
    assert rep["totals"]["unclear"] == 1, rep["unclear"]
    assert rep["unclear"][0]["reading"] == "samma projektskede"
    # bladen bär sina egna id:n, och aldrig lagringsvägen
    assert all(row.get("drawing_id") for row in rep["documents"])
    assert not any("path" in row for row in rep["documents"])

    # husen hålls isär i trädet, och hus A:s blad hamnar aldrig under hus B
    assert set(rep["tree"]) == {"A", "B"}
    assert len(rep["tree"]["A"]["VVS"]) == 3 and len(rep["tree"]["B"]["VVS"]) == 1


def _run_handling(client, H, pid):
    """Starta läsningen och vänta ut den, som gränssnittet gör."""
    a = client.post(f"/api/projects/{pid}/analysis", headers=H).json()
    for _ in range(120):
        a = client.get(f"/api/projects/{pid}/analysis", headers=H).json()
        if a["status"] in ("DONE", "FAILED"):
            break
        time.sleep(0.25)
    assert a["status"] == "DONE", a
    return a["report"]


def test_what_a_person_corrects_about_a_sheet_outranks_what_the_reading_found(client, tmp_path):
    """Mappen hette hus B och innehöll hus C:s ritningar. Läsningen hade rätt - men den har inte alltid rätt.

    En rättelse ligger kvar när analysen körs om, och den ska räkna om det den påverkar: står bladet under fel
    hus efter en rättelse är rättelsen bara en etikett.
    """
    r = client.post("/api/auth/register", json={"email": "rattat@example.com", "password": "hemligt1"}).json()
    H = {"Authorization": f"Bearer {r['access_token']}"}
    p = client.post("/api/projects", json={"name": "Rättat hus", "description": ""}, headers=H).json()
    f = _titled(str(tmp_path / "V-50-1-C0110.pdf"),
                ["V-50-1-C0110", "HUS C, PLAN 1, RORINSTALLATIONER", "BYGGHANDLING", "2024-05-07"])
    with open(f, "rb") as fh:
        d = client.post(f"/api/projects/{p['id']}/drawings",
                        files={"file": ("V-50-1-C0110.pdf", fh, "application/pdf")}, headers=H).json()

    rep = _run_handling(client, H, p["id"])
    assert rep["buildings"] == ["C"]

    assert client.post(f"/api/projects/{p['id']}/overrides", headers=H,
                       json={"drawing_id": d["id"], "field": "hus", "value": "B"}).status_code == 400
    ok = client.post(f"/api/projects/{p['id']}/overrides", headers=H,
                     json={"drawing_id": d["id"], "field": "building", "value": "B",
                           "note": "mappen heter hus B"}).json()
    assert ok["rerun_needed"] is True, "en rättelse som inte räknats om är bara en etikett"

    rep = _run_handling(client, H, p["id"])
    assert rep["buildings"] == ["B"], "rättelsen går före läsningen"
    row = rep["tree"]["B"]["VVS"][0]
    assert row["building"]["where"] == "rättelse", "och det syns att det var en människa som sa det"

    rows = client.get(f"/api/projects/{p['id']}/overrides", headers=H).json()["rows"]
    assert len(rows) == 1 and rows[0]["note"] == "mappen heter hus B"


def test_another_reader_cannot_read_or_correct_someone_elses_handling(client, tmp_path):
    """Ett projekt är sitt ägares. Det gäller projektanalysen precis som allt annat."""
    a = client.post("/api/auth/register", json={"email": "min@example.com", "password": "hemligt1"}).json()
    HA = {"Authorization": f"Bearer {a['access_token']}"}
    b = client.post("/api/auth/register", json={"email": "din@example.com", "password": "hemligt1"}).json()
    HB = {"Authorization": f"Bearer {b['access_token']}"}
    p = client.post("/api/projects", json={"name": "Mitt", "description": ""}, headers=HA).json()
    for h, code in ((HB, 404), (HA, 200)):
        assert client.get(f"/api/projects/{p['id']}/mode", headers=h).status_code == code
    assert client.post(f"/api/projects/{p['id']}/analysis", headers=HB).status_code == 404
    assert client.get(f"/api/projects/{p['id']}/overrides", headers=HB).status_code == 404


def test_a_change_list_needs_two_readings_and_never_fills_in_the_missing_one(client, tmp_path, synthetic_pdf):
    """Ett par utan två mängdade blad har ingen ändringslista, och får inte låtsas ha en.

    Fylls den saknade sidan i med noll blir varje beteckning på den lästa sidan "tillkommen" eller
    "borttagen", och den listan ser ut precis som en riktig ändringslista. Så länge bara ena sidan är läst
    står det att jämförelsen inte går att göra, och vilken sida som saknas.
    """
    r = client.post("/api/auth/register", json={"email": "andring@example.com", "password": "hemligt1"}).json()
    H = {"Authorization": f"Bearer {r['access_token']}"}
    p = client.post("/api/projects", json={"name": "Revision", "description": ""}, headers=H).json()

    # samma blad i två revisioner: A och B. Revisionsbeteckningen bär ordningen, så det blir ett par.
    ids = {}
    for rev, name in (("A", "rev-a.pdf"), ("B", "rev-b.pdf")):
        f = _titled(str(tmp_path / name),
                    ["V-50-1-A0130", "HUS A, PLAN 1, RORINSTALLATIONER", "BYGGHANDLING",
                     f"REV {rev}", "2024-05-07"])
        with open(f, "rb") as fh:
            ids[rev] = client.post(f"/api/projects/{p['id']}/drawings",
                                   files={"file": (name, fh, "application/pdf")}, headers=H).json()["id"]

    rep = _run_handling(client, H, p["id"])
    assert rep["totals"]["pairs"] == 1, rep["pairs"] or rep["unclear"]
    key = rep["pairs"][0]["key"]

    ch = client.get(f"/api/projects/{p['id']}/analysis/changes?key={key}", headers=H).json()["changes"]
    assert ch["state"] == "OLÄST", ch
    assert set(ch["missing"]) == {"before", "after"}, ch
    assert "rows" not in ch, "en jämförelse som inte gick att göra har inga rader"

    # en sida mängdad räcker inte heller - då vore hela den sidan 'tillkommen'
    j = client.post(f"/api/drawings/{ids['B']}/analyze", headers=H).json()
    for _ in range(120):
        j = client.get(f"/api/jobs/{j['id']}", headers=H).json()
        if j["status"] in ("COMPLETED", "FAILED"):
            break
        time.sleep(0.5)
    ch = client.get(f"/api/projects/{p['id']}/analysis/changes?key={key}", headers=H).json()["changes"]
    assert ch["state"] == "OLÄST" and ch["missing"] == ["before"], ch

    # och ett par som aldrig gick att ordna har ingen ändringslista alls
    assert client.get(f"/api/projects/{p['id']}/analysis/changes?key=finns-inte",
                      headers=H).status_code == 404


def test_two_readings_of_the_same_sheet_are_compared_without_inventing_a_change(client, tmp_path, synthetic_pdf):
    """Samma ritning i två revisioner, båda mängdade: ingenting har ändrats, och det ska listan säga.

    Två läsningar av samma oförändrade rör kan skilja sig något åt, och den spridningen får aldrig redovisas
    som en projektändring.
    """
    r = client.post("/api/auth/register", json={"email": "lika@example.com", "password": "hemligt1"}).json()
    H = {"Authorization": f"Bearer {r['access_token']}"}
    p = client.post("/api/projects", json={"name": "Oförändrat", "description": ""}, headers=H).json()

    ids = {}
    for rev in ("A", "B"):
        with open(synthetic_pdf, "rb") as fh:
            d = client.post(f"/api/projects/{p['id']}/drawings",
                            files={"file": (f"rev{rev}.pdf", fh, "application/pdf")}, headers=H).json()
        ids[rev] = d["id"]
        # bladet bär ingen namnruta, så revisionen sätts för hand - det är precis vad rättelserna finns till för
        client.post(f"/api/projects/{p['id']}/overrides", headers=H,
                    json={"drawing_id": d["id"], "field": "number", "value": "V-50-1-A0140"})
        j = client.post(f"/api/drawings/{d['id']}/analyze", headers=H).json()
        for _ in range(120):
            j = client.get(f"/api/jobs/{j['id']}", headers=H).json()
            if j["status"] in ("COMPLETED", "FAILED"):
                break
            time.sleep(0.5)
        assert j["status"] == "COMPLETED", j

    rep = _run_handling(client, H, p["id"])
    # båda bladen är identiska och bär ingen ordning: de blir oklara, inte ett par - och det är rätt svar
    assert rep["totals"]["pairs"] == 0 and rep["totals"]["unclear"] == 1, (rep["pairs"], rep["unclear"])

    # jämförelsen i sig, på två läsningar av exakt samma ritning: ingen rad får heta ändrad
    from app.db import SessionLocal
    from app.projects_api import _changes
    db = SessionLocal()
    try:
        ch = _changes(db, ids["A"], ids["B"])
    finally:
        db.close()
    assert ch["state"] == "JÄMFÖRD"
    assert ch["totals"]["added"] == 0 and ch["totals"]["removed"] == 0, ch["totals"]
    assert ch["totals"]["changed"] == 0, [r for r in ch["rows"] if r["what"] == "ÄNDRAD"]
    assert ch["totals"]["unchanged"] > 0, ch["totals"]
