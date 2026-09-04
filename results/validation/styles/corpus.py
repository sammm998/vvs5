"""Run every page of every drawing and record what the engine made of it."""
import sys, os, json, time, traceback, signal
sys.path.insert(0, "/home/user/vvs5/engine")
from collections import Counter
from vvs_engine.pdf.extract import extract_document, UnsupportedInputError
from vvs_engine.pipeline import analyze_page

OUT = sys.argv[1]
FILES = sys.argv[2:]
PER_PAGE_TIMEOUT = int(os.environ.get("PAGE_TIMEOUT", "240"))

class Timeout(Exception):
    pass

def _alarm(sig, frm):
    raise Timeout()

signal.signal(signal.SIGALRM, _alarm)

def row(path, idx, rec):
    rec["file"] = path.replace("/home/user/vvs5/", "")
    rec["page"] = idx
    with open(OUT, "a") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(json.dumps({k: rec.get(k) for k in ("file", "page", "state", "scale", "owned_pct", "pipe_m")},
                     ensure_ascii=False), flush=True)

for path in FILES:
    try:
        doc = extract_document(path)
    except UnsupportedInputError as e:
        row(path, -1, {"state": "UNSUPPORTED", "note": str(e)[:200]})
        continue
    except Exception as e:
        row(path, -1, {"state": "EXTRACT_ERROR", "note": f"{type(e).__name__}: {e}"[:200]})
        continue
    for pg in doc.pages:
        t0 = time.time()
        signal.alarm(PER_PAGE_TIMEOUT)
        try:
            pa = analyze_page(pg)
            signal.alarm(0)
            mpp = pa.scale.meters_per_pt
            st = Counter()
            for fk, states in pa.ownership.prim_states.items():
                for pid, s in states.items():
                    st[s.state] += pa.graphs[fk].prims[pid].seg.length * (mpp or 0.0)
            tot = sum(st.values())
            lg = pa.legend
            pipe_des = [d for d in pa.designations
                        if lg.names_a_pipe(d) and (d.text or "").upper() not in lg.components()]
            ver = {a.designation_id for a in pa.anchors if a.state == "VERIFIED_PIPE_ATTACHMENT"}
            q = sorted(pa.quantities, key=lambda r: -r["confirmed_total_m"])[:8]
            row(path, pg.info.index, {
                "state": "OK",
                "seconds": round(time.time() - t0, 1),
                "scale": f"{pa.scale.state}:{round(mpp * 72 / 0.0254, 1) if mpp else None}",
                "legend_entries": len(lg.entries), "legend_systems": sorted(lg.systems()),
                "n_designations": len(pa.designations), "n_pipe_labels": len(pipe_des),
                "n_pipe_labels_attached": sum(1 for d in pipe_des if d.did in ver),
                "anchors": dict(Counter(a.state for a in pa.anchors)),
                "pipe_families": sorted(pa.pipe_families),
                "pipe_m": round(tot, 1), "owned_m": round(st["CONFIRMED"], 1),
                "owned_pct": round(100 * st["CONFIRMED"] / tot) if tot else None,
                "ambiguous_m": round(st["AMBIGUOUS"], 1), "unowned_m": round(st["UNOWNED"], 1),
                "top": [(r["designation"], round(r["confirmed_total_m"], 1)) for r in q],
            })
        except Timeout:
            signal.alarm(0)
            row(path, pg.info.index, {"state": "TIMEOUT", "seconds": PER_PAGE_TIMEOUT})
        except Exception as e:
            signal.alarm(0)
            row(path, pg.info.index, {"state": "ERROR", "seconds": round(time.time() - t0, 1),
                                      "note": f"{type(e).__name__}: {e}"[:300],
                                      "trace": traceback.format_exc()[-700:]})
