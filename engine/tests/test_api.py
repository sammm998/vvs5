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


# ----------------------------------------------------------------------------------------------------------
# akademin
# ----------------------------------------------------------------------------------------------------------

def test_academy_progress_lives_on_the_account_and_the_score_is_the_servers(client):
    """Framstegen låg i webbläsarens eget lager, och en kollega som bytte dator började om från noll.

    Poängen räknas på servern ur stegen själva. Ett resultat som klienten får bestämma är inte ett resultat,
    det är ett önskemål - och en utmärkelse som går att sätta själv är ingen utmärkelse.
    """
    r = client.post("/api/auth/register", json={"email": "elev@example.com", "password": "hemligt1"}).json()
    H = {"Authorization": f"Bearer {r['access_token']}"}
    assert client.get("/api/academy/progress").status_code == 401

    empty = client.get("/api/academy/progress", headers=H).json()
    assert empty["courses"] == {} and empty["score"] == 0 and empty["awards"] == []

    # rätt på första försöket är värt mer än rätt till slut
    a = client.put("/api/academy/progress/system", headers=H,
                   json={"step_id": "system-vad", "right": True, "tries": 1, "of_steps": 3}).json()
    b = client.put("/api/academy/progress/system", headers=H,
                   json={"step_id": "system-tryck", "right": True, "tries": 3, "of_steps": 3}).json()
    assert a["score"] == 10 and b["score"] == 14, (a["score"], b["score"])
    assert b["completed"] is False, "två av tre steg är inte en klarad kurs"
    assert "forsta-steget" in b["awards"], b["awards"]

    done = client.put("/api/academy/progress/system", headers=H,
                      json={"step_id": "system-sjalvfall", "right": True, "tries": 1, "of_steps": 3}).json()
    assert done["completed"] is True
    assert "kursen-klar" in done["awards"]
    assert any(x["key"] == "kursen-klar" for x in done["new_awards"]), done["new_awards"]

    # ett klarat steg blir aldrig oklarat av ett senare besök
    again = client.put("/api/academy/progress/system", headers=H,
                       json={"step_id": "system-vad", "right": False, "tries": 9}).json()
    assert again["done_steps"]["system-vad"]["right"] is True
    assert again["completed"] is True and again["score"] == done["score"]

    all_of_it = client.get("/api/academy/progress", headers=H).json()
    assert set(all_of_it["courses"]) == {"system"} and all_of_it["score"] == done["score"]

    # och en annan elevs framsteg är inte mina
    o = client.post("/api/auth/register", json={"email": "elev2@example.com", "password": "hemligt1"}).json()
    other = client.get("/api/academy/progress",
                       headers={"Authorization": f"Bearer {o['access_token']}"}).json()
    assert other["courses"] == {} and other["score"] == 0


def test_the_award_list_says_what_is_still_locked(client):
    """En låst utmärkelse som inte syns är ingen morot. Villkoret står, och det prövas mot tabellen."""
    r = client.post("/api/auth/register", json={"email": "utmark@example.com", "password": "hemligt1"}).json()
    H = {"Authorization": f"Bearer {r['access_token']}"}
    rows = client.get("/api/academy/awards", headers=H).json()["awards"]
    assert len(rows) >= 4 and all(a["taken_at"] is None for a in rows)
    assert all(a["why"] for a in rows), "en utmärkelse utan villkor går inte att sikta på"
    client.put("/api/academy/progress/system", headers=H, json={"step_id": "x", "right": True})
    rows = client.get("/api/academy/awards", headers=H).json()["awards"]
    assert next(a for a in rows if a["key"] == "forsta-steget")["taken_at"]
    assert next(a for a in rows if a["key"] == "kursen-klar")["taken_at"] is None


def test_a_commission_becomes_a_payout_without_the_amount_passing_through_a_screen(client):
    """Provisionen räknades fram men gick aldrig att betala ut: gränssnittet kunde bara markera en utbetalning
    som redan fanns, och ingen väg skapade någon.

    Beloppet räknas på servern, i ören, ur samma funktion som visar provisionen. Ett belopp som någon skrivit
    av från en skärm är ett belopp som inte går att härleda till en rad.
    """
    from app.db import SessionLocal, User
    r = client.post("/api/auth/register", json={"email": "prov@example.com", "password": "hemligt1"}).json()
    H = {"Authorization": f"Bearer {r['access_token']}"}
    db = SessionLocal()
    u = db.query(User).filter(User.email == "prov@example.com").first()
    u.role = "admin"; db.commit(); db.close()

    p = client.post("/api/admin/partners", headers=H,
                    json={"name": "Anna", "email": "anna@x.se", "kind": "ambassador", "code": "ANNA10",
                          "discount_pct": 10, "commission_pct": 20, "commission_months": 0}).json()
    a = client.post("/api/admin/accounts", headers=H, json={"name": "Kunden", "plan": "proffs"}).json()
    client.put(f"/api/admin/accounts/{a['id']}", headers=H,
               json={"plan": "proffs", "status": "aktiv", "mrr_ore": 199900, "partner_id": p["id"]})

    row = next(x for x in client.get("/api/admin/partners", headers=H).json()["rows"] if x["id"] == p["id"])
    assert row["monthly_commission_ore"] == 39980, row          # 20 % av 1 999,00 kr, räknat i ören
    assert row["monthly_commission_kr"] == 399.80

    # ingen period alls, och en som inte är en period
    assert client.post("/api/admin/payouts/draft", headers=H,
                       json={"partner_id": p["id"], "period": "augusti"}).status_code == 400

    out = client.post("/api/admin/payouts/draft", headers=H,
                      json={"partner_id": p["id"], "period": "2026-08"})
    assert out.status_code == 200, out.text
    assert out.json()["amount_kr"] == 399.80

    # två utbetalningar för samma månad är en dubbelbetalning ingen upptäcker förrän partnern hör av sig
    again = client.post("/api/admin/payouts/draft", headers=H,
                        json={"partner_id": p["id"], "period": "2026-08"})
    assert again.status_code == 400 and "2026-08" in again.json()["detail"]

    rows = client.get("/api/admin/payouts", headers=H).json()["rows"]
    assert len(rows) == 1 and rows[0]["status"] == "oppen" and rows[0]["amount_kr"] == 399.80
    client.put(f"/api/admin/payouts/{out.json()['id']}?status=utbetald", headers=H)
    row = next(x for x in client.get("/api/admin/partners", headers=H).json()["rows"] if x["id"] == p["id"])
    assert row["paid_total_ore"] == 39980, "det utbetalda ska synas på partnern"


def test_a_markup_is_measured_by_the_server_and_never_by_the_browser(client, synthetic_pdf):
    """Egna markeringar ligger vid sidan av läsningen, aldrig i den - och mäts där skalan finns.

    Ett mått som klienten räknar fram går inte att härleda till någonting, och det skulle stå bredvid motorns
    meter i samma tabell. Utan en färdig läsning finns ingen skala, och då redovisas markeringen i punkter med
    ett uttryckligt "ingen skala" i stället för i påhittade meter.
    """
    r = client.post("/api/auth/register", json={"email": "mark@example.com", "password": "hemligt1"}).json()
    H = {"Authorization": f"Bearer {r['access_token']}"}
    p = client.post("/api/projects", json={"name": "Markering", "description": ""}, headers=H).json()
    with open(synthetic_pdf, "rb") as fh:
        d = client.post(f"/api/projects/{p['id']}/drawings",
                        files={"file": ("m.pdf", fh, "application/pdf")}, headers=H).json()

    # före läsningen: inga meter, och det står varför
    first = client.post(f"/api/drawings/{d['id']}/markups", headers=H,
                        json={"tool": "langd", "points": [[0, 0], [100, 0]]}).json()
    assert first["measure"]["scale"] == "INGEN_SKALA"
    assert first["measure"]["langd_pt"] == 100.0 and "m" not in first["measure"]

    j = client.post(f"/api/drawings/{d['id']}/analyze", headers=H).json()
    for _ in range(240):
        j = client.get(f"/api/jobs/{j['id']}", headers=H).json()
        if j["status"] in ("COMPLETED", "FAILED"):
            break
        time.sleep(0.5)
    assert j["status"] == "COMPLETED", j
    mpp = client.get(f"/api/jobs/{j['id']}/result", headers=H).json()["scale"]["meters_per_pdf_point"]

    line = client.post(f"/api/drawings/{d['id']}/markups", headers=H,
                       json={"tool": "langd", "designation": "KV01", "points": [[0, 0], [100, 0], [100, 50]]}).json()
    assert line["measure"]["scale"] == "VERIFIERAD"
    assert abs(line["measure"]["m"] - 150.0 * mpp) <= 5e-4, line["measure"]

    # en yta räknas på den slutna formen: en kvadrat på hundra punkter är hundra gånger hundra
    box = client.post(f"/api/drawings/{d['id']}/markups", headers=H,
                      json={"tool": "area", "points": [[0, 0], [100, 0], [100, 100], [0, 100]]}).json()
    assert abs(box["measure"]["area_pt"] - 10000.0) < 1e-6
    assert abs(box["measure"]["kvm"] - 10000.0 * mpp * mpp) <= 5e-4

    n = client.post(f"/api/drawings/{d['id']}/markups", headers=H,
                    json={"tool": "antal", "points": [[1, 1], [2, 2], [3, 3]]}).json()
    assert n["measure"]["antal"] == 3

    # ett okänt verktyg lagras inte som något gränssnittet sedan tyst hoppar över
    assert client.post(f"/api/drawings/{d['id']}/markups", headers=H,
                       json={"tool": "hitta-på", "points": []}).status_code == 400
    assert client.post(f"/api/drawings/{d['id']}/markups", headers=H,
                       json={"tool": "langd", "points": [[1, 2, 3]]}).status_code == 400

    rows = client.get(f"/api/drawings/{d['id']}/markups?page=0", headers=H).json()
    assert len(rows["rows"]) == 4 and rows["meters_per_pdf_point"] == mpp
    assert abs(rows["totals"]["m"] - round(150.0 * mpp, 3)) < 0.02, rows["totals"]

    # ändras punkterna räknas måttet om - klienten skickar aldrig med ett mått
    moved = client.put(f"/api/drawings/{d['id']}/markups/{line['id']}", headers=H,
                       json={"tool": "langd", "points": [[0, 0], [50, 0]]}).json()
    assert abs(moved["measure"]["m"] - 50.0 * mpp) <= 5e-4

    client.delete(f"/api/drawings/{d['id']}/markups/{line['id']}", headers=H)
    assert len(client.get(f"/api/drawings/{d['id']}/markups", headers=H).json()["rows"]) == 3

    # och en annan mängdares markeringar är inte mina
    o = client.post("/api/auth/register", json={"email": "mark2@example.com", "password": "hemligt1"}).json()
    OH = {"Authorization": f"Bearer {o['access_token']}"}
    assert client.get(f"/api/drawings/{d['id']}/markups", headers=OH).status_code == 404
    assert client.post(f"/api/drawings/{d['id']}/markups", headers=OH,
                       json={"tool": "langd", "points": [[0, 0], [1, 1]]}).status_code == 404


def test_the_service_refuses_to_run_on_the_secret_that_is_in_the_source(client):
    """Ett bevis undertecknat med en publik sträng är inget bevis.

    Standardnyckeln står i källkoden. Startar tjänsten i drift med den kan vem som helst som läst koden skriva
    sitt eget inloggningsbevis för vilket konto som helst - adminkontot inräknat - och ingenting i tjänsten
    skulle märka det. Varken inloggningen, ägarkontrollen eller adminspärren tittar på annat än signaturen.

    Ett varningsmeddelande i en logg ingen läser är samma sak som ingenting, så tjänsten går inte upp alls.
    På en utvecklingsmaskin är standardvärdet däremot precis vad man vill ha.

    (`client` tas in för att den lägger backend på importvägen, inte för att provet gör något anrop.)
    """
    import os as _os
    from app import config

    real = dict(_os.environ)
    try:
        for k in ("VVS_DEV", "PYTEST_CURRENT_TEST", "RAILWAY_ENVIRONMENT", "RAILWAY_PROJECT_ID",
                  "RAILWAY_SERVICE_ID", "FLY_APP_NAME", "RENDER", "HEROKU_APP_NAME",
                  "KUBERNETES_SERVICE_HOST", "VVS_PRODUCTION"):
            _os.environ.pop(k, None)
        was = config.settings.secret_key

        # en utvecklingsmaskin: ingenting säger drift, och standardnyckeln duger
        config.settings.secret_key = config.DEV_SECRET
        config.demand_a_real_secret()

        # men på en driftplattform ska den inte gå upp
        _os.environ["RAILWAY_ENVIRONMENT"] = "production"
        try:
            config.demand_a_real_secret()
            raise AssertionError("tjänsten startade med källkodens nyckel i drift")
        except RuntimeError as e:
            assert "VVS_SECRET_KEY" in str(e), e

        # och med en riktig nyckel går den upp igen
        config.settings.secret_key = "en-lang-slumpstrang-som-ingen-last-i-koden"
        config.demand_a_real_secret()
        config.settings.secret_key = was
    finally:
        _os.environ.clear()
        _os.environ.update(real)


def test_a_file_that_is_not_the_expected_drawing_answers_in_a_sentence(client, tmp_path):
    """Den sortens fil en kund laddar upp först.

    Ett tydligt fel är ett svar. En stackspårning i felrutan är det inte: den säger ingenting till en mängdare
    och lämnar ut serverns filvägar och moduler på köpet. Och en lösenordsskyddad PDF ska stoppas där den
    laddas upp, inte falla på jobbkön långt från den som skickade den.
    """
    import pymupdf
    r = client.post("/api/auth/register", json={"email": "skrap@example.com", "password": "hemligt1"}).json()
    H = {"Authorization": f"Bearer {r['access_token']}"}
    p = client.post("/api/projects", json={"name": "Skräp", "description": ""}, headers=H).json()

    def up(name, data):
        return client.post(f"/api/projects/{p['id']}/drawings",
                           files={"file": (name, data, "application/pdf")}, headers=H)

    assert up("tom.pdf", b"").status_code == 400
    assert up("text.pdf", b"det har ar inte en pdf alls\n" * 40).status_code == 400
    assert up("bild.png", b"%PDF-1.4 ...").status_code == 400, "bara PDF stöds"

    lock = str(tmp_path / "las.pdf")
    d = pymupdf.open(); d.new_page(width=842, height=595)
    d.save(lock, encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw="o", user_pw="u"); d.close()
    with open(lock, "rb") as fh:
        r2 = up("las.pdf", fh.read())
    assert r2.status_code == 400
    assert "lösenordsskyddad" in r2.json()["detail"], r2.json()

    # en giltig men tom vektorritning tas emot och avvisas av läsningen, med ett skäl en mängdare förstår
    blank = str(tmp_path / "blank.pdf")
    d = pymupdf.open(); d.new_page(width=842, height=595); d.save(blank); d.close()
    with open(blank, "rb") as fh:
        got = up("blank.pdf", fh.read())
    assert got.status_code == 200, got.text
    j = client.post(f"/api/drawings/{got.json()['id']}/analyze", headers=H).json()
    for _ in range(240):
        j = client.get(f"/api/jobs/{j['id']}", headers=H).json()
        if j["status"] in ("COMPLETED", "FAILED"):
            break
        time.sleep(0.4)
    assert j["status"] == "FAILED", j["status"]
    assert j["error"] and "vektor" in j["error"].lower(), j["error"]
    assert "Traceback" not in j["error"] and "/home/" not in j["error"] and ".py" not in j["error"], (
        "felrutan visas för kunden; en stackspårning där lämnar ut serverns insida")


def test_every_export_actually_opens_in_the_program_it_is_meant_for(client, synthetic_pdf):
    """Ett svar med status 200 är inte en fil som går att öppna.

    Excel-filen ska gå att läsa med openpyxl och bära samma beteckningar som resultatet; CSV:n ska ha en
    BOM så Excel läser å, ä och ö rätt, och lika många rader; JSON:en ska vara JSON; PDF:en ska ha sidor;
    rapporten ska nämna ritningen. Det är vad mängdaren gör med filen sekunden efter nedladdningen.
    """
    import csv
    import io
    import json as _json

    import openpyxl
    import pymupdf

    r = client.post("/api/auth/register", json={"email": "export@example.com", "password": "hemligt1"}).json()
    H = {"Authorization": f"Bearer {r['access_token']}"}
    p = client.post("/api/projects", json={"name": "Export", "description": ""}, headers=H).json()
    with open(synthetic_pdf, "rb") as fh:
        d = client.post(f"/api/projects/{p['id']}/drawings",
                        files={"file": ("Kv Björken plan 2.pdf", fh, "application/pdf")}, headers=H).json()
    j = client.post(f"/api/drawings/{d['id']}/analyze", headers=H).json()
    for _ in range(240):
        j = client.get(f"/api/jobs/{j['id']}", headers=H).json()
        if j["status"] in ("COMPLETED", "FAILED"):
            break
        time.sleep(0.5)
    assert j["status"] == "COMPLETED", j
    res = client.get(f"/api/jobs/{j['id']}/result", headers=H).json()
    names = {q["designation"] for q in res["quantities"]}
    assert names

    x = client.get(f"/api/jobs/{j['id']}/export/xlsx", headers=H)
    assert x.status_code == 200
    assert 'filename="' in x.headers.get("content-disposition", ""), "utan filnamn heter filen 'download'"
    wb = openpyxl.load_workbook(io.BytesIO(x.content), data_only=True)
    cells = {str(c.value) for ws in wb.worksheets for row in ws.iter_rows() for c in row if c.value is not None}
    assert names <= cells, f"beteckningar som inte kom med i Excel: {names - cells}"

    c = client.get(f"/api/jobs/{j['id']}/export/csv", headers=H)
    assert c.content.startswith(b"\xef\xbb\xbf"), "utan BOM läser Excel svenska tecken fel"
    # semikolon, för svensk Excel: kommat är decimaltecknet där, och en kommaseparerad fil blir en enda kolumn
    rows = list(csv.reader(io.StringIO(c.content.decode("utf-8-sig")), delimiter=";"))
    assert len(rows) >= 1 + len(names), f"{len(rows)} rader för {len(names)} beteckningar"
    assert names <= {cell for row in rows for cell in row}

    js = client.get(f"/api/jobs/{j['id']}/export/json", headers=H)
    body = _json.loads(js.content)
    assert {q["designation"] for q in body["rows"]} == names

    pdf = client.get(f"/api/jobs/{j['id']}/export/pdf", headers=H)
    doc = pymupdf.open(stream=pdf.content, filetype="pdf")
    assert len(doc) >= 1, "den markerade PDF:en har inga sidor"
    doc.close()

    rep = client.get(f"/api/jobs/{j['id']}/export/report", headers=H)
    assert rep.status_code == 200
    text = rep.content.decode("utf-8", "replace")
    assert "Björken" in text or "Bj\\u00f6rken" in text, "rapporten nämner inte ritningen"
    assert any(n in text for n in names), "rapporten nämner ingen av beteckningarna"


def test_a_guesser_is_slowed_down_and_cannot_tell_which_accounts_exist(client):
    """Ett lösenord på sex tecken tål inte obegränsat många försök.

    Efter tio fel på en adress inom en kvart svarar tjänsten 429 med hur länge - också på det rätta lösenordet,
    för det är just då gissaren har hittat det. Och en adress som inte finns kostar lika lång tid som en som
    finns med fel lösenord; utan det säger svarstiden vilka konton som finns.
    """
    import time as _t
    from app import auth
    client.post("/api/auth/register", json={"email": "gissa@example.com", "password": "hemligt1"})

    # samma svar, och ungefär samma tid, för en okänd adress och ett fel lösenord
    t0 = _t.perf_counter(); a = client.post("/api/auth/login", data={"username": "gissa@example.com", "password": "fel"}); ta = _t.perf_counter() - t0
    t0 = _t.perf_counter(); b = client.post("/api/auth/login", data={"username": "finns-inte@example.com", "password": "fel"}); tb = _t.perf_counter() - t0
    assert a.status_code == b.status_code == 401 and a.json() == b.json()
    assert tb > 0.4 * ta, f"den okända adressen svarade på {tb*1000:.0f} ms mot {ta*1000:.0f} ms: tiden avslöjar kontot"

    auth._fails.clear()
    for _ in range(auth.LOGIN_MAX_FAILS - 1):
        assert client.post("/api/auth/login", data={"username": "gissa@example.com", "password": "fel"}).status_code == 401
    # det tionde felet fyller fönstret; därefter är dörren stängd - även för rätt lösenord
    assert client.post("/api/auth/login", data={"username": "gissa@example.com", "password": "fel"}).status_code == 401
    r = client.post("/api/auth/login", data={"username": "gissa@example.com", "password": "hemligt1"})
    assert r.status_code == 429, r.text
    assert "Retry-After" in r.headers and "minuter" in r.json()["detail"]

    # ett annat konto från samma håll spärras inte av det - spärren per avsändare är mycket vidare
    client.post("/api/auth/register", json={"email": "annan-gissa@example.com", "password": "hemligt1"})
    assert client.post("/api/auth/login", data={"username": "annan-gissa@example.com", "password": "hemligt1"}).status_code == 200

    # och när fönstret gått ut öppnas dörren igen, och ett lyckat försök nollar räkningen
    auth._fails.clear()
    assert client.post("/api/auth/login", data={"username": "gissa@example.com", "password": "hemligt1"}).status_code == 200


def test_a_storage_key_cannot_reach_outside_the_root_not_even_a_sibling_with_the_same_prefix(tmp_path):
    """Ett prefix utan avskiljare släpper igenom grannen.

    Med roten /data/storage dög /data/storage2/x som "innanför", för strängen börjar ju likadant. Nyckeln
    "../storage2/x" nådde alltså en katalog bredvid lagret. Antingen roten själv, eller något under den med
    avskiljaren emellan - ingenting annat.
    """
    import os
    import pytest
    from app.storage import LocalStorage
    root = tmp_path / "storage"
    (tmp_path / "storage2").mkdir()
    st = LocalStorage(str(root))
    assert st.path("drawings/x/y.pdf").startswith(str(root) + os.sep)
    for bad in ("../storage2/x", "../../etc/passwd", "/etc/passwd", "..", "../storage2"):
        with pytest.raises(ValueError):
            st.path(bad)
    assert st.path("") == str(root) or st.path(".") == str(root)


def test_the_project_agent_answers_from_the_reading_and_names_its_sheets(client, tmp_path):
    """Projektagentens verktyg utan modell: svaren kommer ur rapporten och nämner bladen de vilar på.

    Före en projektanalys finns inget att svara ur, och då är det ett tydligt nej (409) - agenten svarar
    aldrig ur något annat än det som lästs. Och en främling får inte fråga (404).
    """
    r = client.post("/api/auth/register", json={"email": "agent@example.com", "password": "hemligt1"}).json()
    H = {"Authorization": f"Bearer {r['access_token']}"}
    p = client.post("/api/projects", json={"name": "Agentprojekt", "description": ""}, headers=H).json()
    for name, lines in {
        "V-50-1-A0111.pdf": ["V-50-1-A0111", "HUS A, PLAN 1, RORINSTALLATIONER", "BYGGHANDLING", "2024-05-07"],
        "V-50-1-B0112.pdf": ["V-50-1-B0112", "HUS B, PLAN 1, RORINSTALLATIONER", "BYGGHANDLING", "2024-05-07"],
    }.items():
        f = _titled(str(tmp_path / name), lines)
        with open(f, "rb") as fh:
            client.post(f"/api/projects/{p['id']}/drawings", files={"file": (name, fh, "application/pdf")}, headers=H)

    # ingen analys ännu: inget att svara ur
    r0 = client.post(f"/api/projects/{p['id']}/agent/tool", headers=H, json={"name": "hamta_handling"})
    assert r0.status_code == 409, r0.text

    _run_handling(client, H, p["id"])
    tools = client.get(f"/api/projects/{p['id']}/agent/tools", headers=H).json()["tools"]
    assert {t["name"] for t in tools} >= {"hamta_handling", "hitta_blad", "mangder_per_hus", "versioner",
                                          "vad_andrades", "kontrollera_handlingen"}

    h = client.post(f"/api/projects/{p['id']}/agent/tool", headers=H, json={"name": "hamta_handling"}).json()
    res = h["verktyg"][0]["resultat"]
    assert res["hus"] == ["A", "B"] and res["totalt"]["documents"] == 2
    assert len(res["blad_utan_lasning"]) == 2, "inget blad är mängdat ännu, och det ska stå"

    b = client.post(f"/api/projects/{p['id']}/agent/tool", headers=H,
                    json={"name": "hitta_blad", "arguments": {"hus": "B"}}).json()["verktyg"][0]["resultat"]
    assert b["antal"] == 1 and b["blad"][0]["blad"] == "V-50-1-B0112.pdf", "ett svar om hus B bygger bara på hus B:s blad"
    assert b["blad"][0]["drawing_id"], "varje svar säger vilket blad det vilar på"

    v = client.post(f"/api/projects/{p['id']}/agent/tool", headers=H,
                    json={"name": "vad_andrades", "arguments": {"nyckel": "finns-inte"}}).json()["verktyg"][0]["resultat"]
    assert "fel" in v and v["tillgangliga"] == [], "ett par som inte finns har ingen ändringslista"

    assert client.post(f"/api/projects/{p['id']}/agent/tool", headers=H,
                       json={"name": "hitta_på"}).status_code == 404

    o = client.post("/api/auth/register", json={"email": "agent2@example.com", "password": "hemligt1"}).json()
    assert client.post(f"/api/projects/{p['id']}/agent/tool", json={"name": "hamta_handling"},
                       headers={"Authorization": f"Bearer {o['access_token']}"}).status_code == 404


def test_a_calculation_prices_the_reading_and_the_tender_carries_the_same_numbers(client, synthetic_pdf):
    """Från mängd till anbud, med varje steg utskrivet.

    Kalkylen räknar ur läsningens rader: artikel ur materialboken, timmar ur Normtid VVS, spill, påslag och
    moms - och summan är summan av delarna. Anbudet skrivs ur den SPARADE kalkylen och bär samma tal; utan en
    sparad kalkyl finns inget anbud. En annan användare får varken räkna eller läsa.
    """
    import pymupdf
    r = client.post("/api/auth/register", json={"email": "kalkyl@example.com", "password": "hemligt1"}).json()
    H = {"Authorization": f"Bearer {r['access_token']}"}
    p = client.post("/api/projects", json={"name": "Kv Björken", "description": ""}, headers=H).json()
    with open(synthetic_pdf, "rb") as fh:
        d = client.post(f"/api/projects/{p['id']}/drawings",
                        files={"file": ("plan2.pdf", fh, "application/pdf")}, headers=H).json()
    j = client.post(f"/api/drawings/{d['id']}/analyze", headers=H).json()
    for _ in range(240):
        j = client.get(f"/api/jobs/{j['id']}", headers=H).json()
        if j["status"] in ("COMPLETED", "FAILED"):
            break
        time.sleep(0.5)
    assert j["status"] == "COMPLETED", j

    u = client.get(f"/api/jobs/{j['id']}/calc/underlag", headers=H).json()
    assert u["defaults"]["timpris"] > 0 and u["normtid"]["tables"], "underlaget bär boken och antagandena"
    assert client.get(f"/api/jobs/{j['id']}/calc", headers=H).json()["status"] == "NONE"
    assert client.get(f"/api/jobs/{j['id']}/calc/anbud.pdf", headers=H).status_code == 409, "inget anbud utan sparad kalkyl"

    c = client.post(f"/api/jobs/{j['id']}/calc/preview", headers=H,
                    json={"assumptions": {"timpris": 700, "spill_pct": 10, "paslag_material_pct": 10,
                                          "paslag_arbete_pct": 0, "moms_pct": 25, "supplements": ["pressfog"]}}).json()
    rows, T = c["rows"], c["totals"]
    assert rows and T["rader"] == len(rows)
    # varje rad: kalkylmängd = netto + spill, och summan är summan av delarna
    for row in rows:
        assert abs(row["kalkyl_m"] - row["netto_m"] * 1.10) < 0.02, row
        assert abs(row["summa_kr"] - ((row["material_kr"] or 0) + (row["arbete_kr"] or 0))) < 0.02
        if row["timmar"] is not None and not row["timmar_for_hand"]:
            assert row["steg"]["tillagg_pct"] == 15.0, "pressfog är +15 % i boken"
            assert abs(row["arbete_kr"] - row["timmar"] * 700) < 0.02
    with_time = [x for x in rows if x["timmar"] is not None]
    assert with_time, "minst en dimension i bladet ska ha en normtid i boken"
    mat = sum(x["material_kr"] or 0 for x in rows); arb = sum(x["arbete_kr"] or 0 for x in rows)
    assert abs(T["material_kr"] - mat) < 0.05 and abs(T["arbete_kr"] - arb) < 0.05
    assert abs(T["netto_kr"] - (mat * 1.10 + arb)) < 0.05
    assert abs(T["brutto_kr"] - T["netto_kr"] * 1.25) < 0.05

    # en timme skriven för hand går före boken, och en vald artikel går före förslaget
    first = rows[0]["designation"]
    alt = rows[0]["alternativ"][1]["a"] if len(rows[0]["alternativ"]) > 1 else None
    ov = {first: {"timmar": 3.5, **({"artikel": alt} if alt else {})}}
    s = client.put(f"/api/jobs/{j['id']}/calc", headers=H,
                   json={"assumptions": c["assumptions"], "overrides": ov}).json()
    row0 = next(x for x in s["rows"] if x["designation"] == first)
    assert row0["timmar"] == 3.5 and row0["timmar_for_hand"] and row0["normtid_kalla"] == "angiven för hand"
    if alt:
        assert row0["artikel"]["a"] == alt and row0["vald_artikel"]
    assert client.get(f"/api/jobs/{j['id']}/calc", headers=H).json()["status"] == "SAVED"

    pdf = client.get(f"/api/jobs/{j['id']}/calc/anbud.pdf", headers=H)
    assert pdf.status_code == 200 and pdf.headers["content-type"].startswith("application/pdf")
    doc = pymupdf.open(stream=pdf.content, filetype="pdf")
    text = "".join(pg.get_text() for pg in doc)
    assert len(doc) >= 1 and "Anbud" in text and "Kv Björken" in text
    brutto = f"{s['totals']['brutto_kr']:,.2f}".replace(",", " ").replace(".", ",")
    assert brutto in text, f"anbudet ska bära kalkylens summa {brutto}"
    assert "Förbehåll" in text and "Förutsättningar" in text
    assert "ABT 06" in text and "Garantitid" in text, "standardavtalet och dess villkor står i anbudet"
    assert f"Sida 1 av {len(doc)}" in text, "varje sida bär sitt nummer"
    fonts = {f[3] for pg in doc for f in pg.get_fonts()}
    assert any("Liberation" in f for f in fonts), fonts
    html_doc = client.get(f"/api/jobs/{j['id']}/calc/anbud.html", headers=H)
    assert html_doc.status_code == 200 and "ANBUD" in html_doc.text
    info = client.get(f"/api/jobs/{j['id']}/calc/anbud", headers=H).json()
    assert info["pages"] == len(doc) and "AB 04" in info["regelverk"]
    png = client.get(f"/api/jobs/{j['id']}/calc/anbud/sida-1.png", headers=H)
    assert png.status_code == 200 and png.headers["content-type"] == "image/png" and png.content[:8] == b"\x89PNG\r\n\x1a\n"
    assert client.get(f"/api/jobs/{j['id']}/calc/anbud/sida-{len(doc) + 1}.png", headers=H).status_code == 404
    # utan standardavtal: ingen villkorsrubrik, och inget påhittat
    s2 = client.put(f"/api/jobs/{j['id']}/calc", headers=H,
                    json={"assumptions": {**c["assumptions"], "regelverk": ""}, "overrides": ov}).json()
    assert s2["assumptions"]["regelverk"] == ""
    text2 = "".join(pg.get_text() for pg in pymupdf.open(stream=client.get(f"/api/jobs/{j['id']}/calc/anbud.pdf", headers=H).content, filetype="pdf"))
    assert "Avtalsvillkor" not in text2 and "Garantitid" not in text2

    o = client.post("/api/auth/register", json={"email": "kalkyl2@example.com", "password": "hemligt1"}).json()
    OH = {"Authorization": f"Bearer {o['access_token']}"}
    assert client.get(f"/api/jobs/{j['id']}/calc", headers=OH).status_code == 404
    assert client.get(f"/api/jobs/{j['id']}/calc/anbud.pdf", headers=OH).status_code == 404
