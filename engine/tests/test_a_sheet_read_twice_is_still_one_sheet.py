"""Projektpriorn ska räkna källor, inte körningar.

Den läser vad projektets övriga blad har sagt om vilken penna ett system ritas med, och en tröskel avgör när
det är tillräckligt sagt för att ett annat blad ska få luta sig mot det. Tröskeln summerade över JOBB. Ett
blad som analyserades om fem gånger röstade fem gånger, och "flera oberoende blad säger samma sak" kunde
uppfyllas av ett enda - därför att någon tryckte på analysera igen, vilket inte säger något alls om ritningen.

Ett jobb är en läsning. Ett blad är en källa. Den senaste läsningen ERSÄTTER den tidigare; den adderas inte.
"""
import datetime as dt
import json
import os
import sys

import pytest

FAM = "V-52BB--FE-_VS1x-|s|solid"


@pytest.fixture()
def bench(tmp_path, monkeypatch):
    """En egen databas och ett eget lager per prov - inget delas med tjänstens riktiga."""
    monkeypatch.setenv("VVS_DATABASE_URL", f"sqlite:///{tmp_path}/t.db")
    monkeypatch.setenv("VVS_STORAGE_ROOT", str(tmp_path / "storage"))
    monkeypatch.setenv("VVS_SECRET_KEY", "test")
    backend = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
    if backend not in sys.path:
        sys.path.insert(0, backend)
    for m in list(sys.modules):
        if m == "app" or m.startswith("app."):
            del sys.modules[m]
    from app.db import AnalysisJob, Base, Drawing, Project, SessionLocal, User, engine
    from app.storage import storage
    Base.metadata.create_all(engine)
    db = SessionLocal()
    user = User(id="u1", email="p@x", password_hash="x")
    proj = Project(id="p1", owner_id="u1", name="ett hus")
    subject = Drawing(id="d0", project_id="p1", filename="under läsning.pdf", storage_key="k0", sha256="0",
                      size_bytes=1)
    db.add_all([user, proj, subject])
    db.commit()

    def sheet(did: str) -> None:
        db.add(Drawing(id=did, project_id="p1", filename=f"{did}.pdf", storage_key=f"k{did}", sha256=did,
                       size_bytes=1))
        db.commit()

    def run(did: str, times: int, system: str = "VS1", minute: int = 0) -> None:
        """En läsning av ett blad som sade `times` gånger att pennan hör till `system`."""
        jid = f"{did}-{minute}"
        key = f"results/{did}/{jid}"
        os.makedirs(storage.path(key), exist_ok=True)
        with open(os.path.join(storage.path(key), "drawn-system-families.json"), "w", encoding="utf-8") as fh:
            json.dump({"stated": [{"family": FAM, "system": system, "times": times}]}, fh)
        when = dt.datetime(2026, 1, 1, 12, minute, tzinfo=dt.timezone.utc)
        db.add(AnalysisJob(id=jid, drawing_id=did, status="COMPLETED", result_key=key, created_at=when,
                           finished_at=when))
        db.commit()

    yield db, subject, sheet, run
    db.close()


def _families(db, subject) -> dict:
    from app.jobs import project_system_families
    return project_system_families(db, subject)


def test_one_sheet_analysed_five_times_is_not_five_sheets(bench):
    """Kärnan: samma blad, fem körningar. Det är fortfarande ett blad, och ett blad räcker inte."""
    db, subject, sheet, run = bench
    sheet("d1")
    for minute in range(5):
        run("d1", times=3, minute=minute)
    assert _families(db, subject) == {}


def test_two_sheets_that_agree_do_settle_it(bench):
    """Och gränsen ligger rätt: två riktiga blad som säger samma sak är en vana, och den får bäras vidare."""
    db, subject, sheet, run = bench
    for did in ("d1", "d2"):
        sheet(did)
        run(did, times=2)
    from vvs_engine.pipeline import pen_key
    assert _families(db, subject) == {pen_key(FAM): "VS1"}


def test_the_latest_reading_supersedes_the_earlier_one(bench):
    """En omläsning ersätter: sade bladet VS1 i går och VV1 i dag är det VV1 som står, inte båda."""
    db, subject, sheet, run = bench
    for did in ("d1", "d2"):
        sheet(did)
        run(did, times=4, system="VS1", minute=0)
        run(did, times=4, system="VV1", minute=9)
    from vvs_engine.pipeline import pen_key
    assert _families(db, subject) == {pen_key(FAM): "VV1"}


def test_a_re_run_cannot_outvote_a_second_sheet(bench):
    """Det tysta felet: ett blad som körts om många gånger tog över ett annat blads besked.

    Bladet d1 säger VS1 en enda gång, men har lästs om tjugo gånger. Bladet d2 säger VV1 fyra gånger, i en
    läsning. Räknat på körningar vinner d1 med 20 mot 4, passerar andelskravet och installerar VS1 som
    projektets besked. Räknat på källor står det 1 mot 4 - och ett blad är för få.
    """
    db, subject, sheet, run = bench
    sheet("d1")
    sheet("d2")
    for minute in range(20):
        run("d1", times=1, system="VS1", minute=minute)
    run("d2", times=4, system="VV1", minute=0)
    from vvs_engine.pipeline import pen_key
    out = _families(db, subject)
    assert out.get(pen_key(FAM)) != "VS1"
