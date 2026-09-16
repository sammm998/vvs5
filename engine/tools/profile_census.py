"""Ritningsprofilen över hela korpusen: vad bladen faktiskt är för sorts ritningar.

    python3 engine/tools/profile_census.py [ut.json]

Spec avsnitt F ger en referenstabell över elva stilar med pennbredder, ledarbredder och texthöjder. Tabellen är
PipeStudios, mätt på deras material. Det här verktyget mäter samma storheter på VÅRT material, så att de två
går att ställa bredvid varandra i stället för att den ena antas gälla för den andra.

Verktyget ligger i `tools/` och aldrig i `vvs_engine/`: det läser mappar som produktionen inte får känna till,
och kontamineringsskanningen ska förbli PASS.
"""
import json
import os
import sys
import traceback

sys.path.insert(0, "/home/user/vvs5/engine")
from vvs_engine.pdf.extract import extract_document          # noqa: E402
from vvs_engine.profile.style_profile import profile_page    # noqa: E402
from vvs_engine.semantics.annotation import merge_lines, one_reading_per_place   # noqa: E402
from vvs_engine.text.searchable import searchable_rows       # noqa: E402
from vvs_engine.text.vector_text import vector_text_rows     # noqa: E402

ROOT = "/home/user/vvs5/data"


def sheets() -> list[tuple[str, str]]:
    out = []
    for tag in ("A", "C", "D", "E"):
        p = f"{ROOT}/validation_{tag}/clean.pdf"
        if os.path.exists(p):
            out.append((tag, p))
    d3 = f"{ROOT}/validation_set3"
    if os.path.isdir(d3):
        for name in sorted(os.listdir(d3)):
            p = f"{d3}/{name}/clean.pdf"
            if os.path.isfile(p):
                out.append((name, p))
    w = f"{ROOT}/validation_W"
    seen = {t for t, _ in out}
    if os.path.isdir(w):
        for name in sorted(os.listdir(w)):
            p = f"{w}/{name}/clean.pdf"
            if not name.startswith("_") and name not in seen and os.path.isfile(p):
                out.append((name, p))
    return out


def profile_of(pdf: str) -> dict:
    """Profilen utan att köra hela läsningen: texten räcker, och den är den dyra delen ändå.

    Beteckningarna lämnas åt sidan här - de kräver hela etikettkedjan - så höjden mäts på all text och
    profilen säger det själv i `text_height_source`."""
    doc = extract_document(pdf, pages=[0])
    page = doc.pages[0]
    vt: dict = {}
    rows = merge_lines(searchable_rows(page) + vector_text_rows(page, vt).rows, page.info.index)
    rows = one_reading_per_place(rows)
    return profile_page(page, rows=rows).as_dict()


def main() -> None:
    out_path = sys.argv[1] if len(sys.argv) > 1 else ""
    rows = []
    for name, pdf in sheets():
        try:
            pr = profile_of(pdf)
        except Exception as e:                                   # noqa: BLE001
            print(f"{name:22s} FEL {type(e).__name__}: {e}", flush=True)
            traceback.print_exc()
            continue
        pr["sheet"] = name
        rows.append(pr)
        f = pr["paper_factor"]
        print(f"{name:22s} {str(pr['paper_format'] or '?'):3s} {pr['text_mode']:8s} "
              f"text {str(pr['text_height_pt'] or '-'):>5s} pt  faktor {('%.2f' % f) if f else '-':>5s} "
              f"{pr['paper_factor_state']:12s} pennor {len(pr['widths']):2d} "
              f"hårfin {100 * pr['hairline_share']:5.1f}%  kurvandel {100 * pr['curve_share']:4.1f}%", flush=True)
    if out_path:
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, ensure_ascii=False, indent=1)
        print(f"klart: {out_path} ({len(rows)} blad)")


if __name__ == "__main__":
    main()
