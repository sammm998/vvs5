"""Lägg t() runt varje synlig sträng i gränssnittet, och räkna det som återstår.

Gränssnittet är skrivet på svenska och svenskan är översättningsnyckeln (frontend/src/i18n.ts). För att en
sträng ska gå att läsa på engelska måste den gå genom t(). Det här verktyget gör den mekaniska delen: det
hittar texten mellan taggar och i de attribut som visas för en läsare, och lägger t() runt den.

Vad det aldrig rör: klassnamn, id, url:er, api-vägar, nycklar, värden - allt som är kod och inte text. Det
avgörs av vilka attribut som läses (title, placeholder, aria-label, alt, label) och av att texten mellan taggar
varken får innehålla klammer, taggar eller radbrytning.

    python3 frontend/tools/i18n_wrap.py --report          vad som återstår, fil för fil
    python3 frontend/tools/i18n_wrap.py --keys            varje nyckel som saknar engelsk rad
    python3 frontend/tools/i18n_wrap.py --rename          döp om den importerade bindningen till tr
    python3 frontend/tools/i18n_wrap.py src/pages/X.tsx   skriv om en fil (eller flera)

Bindningen heter `tr`, inte `t`. Skälet är mätt: `t` är ett vanligt lokalt namn i den här koden - en
tidtagare, en interpolationsfaktor, ett tillstånd - och i 44 filer finns ett lokalt `t`. Där ett sådant
ligger i samma räckvidd som ett inlagt anrop pekar anropet på det lokala namnet i stället för på ordboken,
och det syns inte i tsc när det lokala värdet är `any`: det kraschar först i webbläsaren. Ett namn som
ingen annan använder gör felet omöjligt i stället för osannolikt.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SRC = os.path.join(ROOT, "src")
BIND = "tr"                                       # namnet den importerade funktionen har i koden
PROPS = ("title", "placeholder", "aria-label", "alt", "label")
# filer som inte är gränssnitt: ordboken själv, ritmotorn, testfixturer
SKIP = ("i18n.ts", ".test.", ".fixture.", "/cad/geom", "vite-env")

TEXT = re.compile(r'([^=!<>+\-*/%&|,])(>)([^<>{}\n]+)(<[A-Za-z/])')
# JS-uttryck ser ut som JSX-text för ett reguljärt uttryck: `{m > 0 ? a : <span>` har ett `>`, text, och ett `<`.
# Skillnaden är att texten då bär operatorer. Bär den någon av de här är den kod, och lämnas i fred.
CODE_CHARS = set("?:()[]=;&|")
PROP = re.compile(r'\b(' + "|".join(p.replace("-", r"\-") for p in PROPS) + r')="([^"\n]+)"')
WORDY = re.compile(r"[A-Za-zÅÄÖåäö]{2,}")
CODEISH = re.compile(r"^[\w.\-/#]+$")            # ett enda ord utan mellanslag: oftast kod, inte text


def wordy(s: str) -> bool:
    s = s.strip()
    if not s or not WORDY.search(s):
        return False
    if CODEISH.match(s) and " " not in s and not re.search(r"[åäöÅÄÖ]", s):
        return False                              # DN, px, id-liknande: lämna
    return True


def wrap(src: str) -> tuple[str, int]:
    n = 0

    def t_text(m):
        nonlocal n
        raw = m.group(3)
        s = raw.strip()
        if not wordy(s) or '"' in s or set(s) & CODE_CHARS:
            return m.group(0)
        n += 1
        lead = raw[: len(raw) - len(raw.lstrip())]
        tail = raw[len(raw.rstrip()):]
        return f'{m.group(1)}{m.group(2)}{lead}{{{BIND}("{s}")}}{tail}{m.group(4)}'

    def t_prop(m):
        nonlocal n
        s = m.group(2).strip()
        if not wordy(s) or '"' in s or "<" in s or ">" in s:
            return m.group(0)
        n += 1
        return f'{m.group(1)}={{{BIND}("{s}")}}'

    src = TEXT.sub(t_text, src)
    src = PROP.sub(t_prop, src)
    return src, n


def ensure_import(src: str, path: str) -> str:
    if re.search(r'from "[^"]*i18n"', src):
        return src
    depth = os.path.relpath(SRC, os.path.dirname(path)).replace("\\", "/")
    rel = "./i18n" if depth == "." else f"{depth}/i18n"
    m = re.search(r'^import .*?;\s*$', src, re.M)
    line = f'import {{ t as {BIND} }} from "{rel}";'
    if m:
        return src[: m.end()] + "\n" + line + src[m.end():]
    return line + "\n" + src


def files() -> list[str]:
    out = []
    for dp, dirs, fs in os.walk(SRC):
        dirs[:] = [d for d in dirs if d != "node_modules"]
        for f in sorted(fs):
            p = os.path.join(dp, f)
            if f.endswith(".tsx") and not any(s in p.replace("\\", "/") for s in SKIP):
                out.append(p)
    return out


IMPORT = re.compile(r'import\s*\{([^}]*)\}\s*from\s*"([^"]*\bi18n)"')
CALL = re.compile(r'(?<![\w$.])t\("')


def rename_one(src: str) -> tuple[str, int]:
    """Byt den importerade `t` mot `tr` i en fil, och varje anrop som hörde till den.

    Ett anrop skrivs om bara i en fil som faktiskt importerar den bara `t`:n. Ligger där ett lokalt `t` i
    vägen är det just de anropen som pekar fel i dag, och de ska med. Ett `t(` som redan är egendom av något
    annat (`x.t(`, `setT(`) rörs inte - därför den negativa blicken bakåt.
    """
    m = IMPORT.search(src)
    if not m:
        return src, 0
    names = [n.strip() for n in m.group(1).split(",") if n.strip()]
    if "t" not in names:
        return src, 0
    fixed = ", ".join("t as " + BIND if n == "t" else n for n in names)
    src = src[: m.start()] + f'import {{ {fixed} }} from "{m.group(2)}"' + src[m.end():]
    src, n = CALL.subn(BIND + '("', src)
    return src, n


def rename() -> None:
    total = 0
    for p in every_file():
        src = open(p, encoding="utf-8").read()
        out, n = rename_one(src)
        if out != src:
            open(p, "w", encoding="utf-8").write(out)
            total += n
            print(f"{n:5d}  {os.path.relpath(p, ROOT)}")
    print(f"\nsumma: {total} anrop döpta till {BIND}()")


def every_file() -> list[str]:
    """Varje modul under src, inte bara .tsx: ordboken talar också i .ts-filer."""
    out = []
    for dp, dirs, fs in os.walk(SRC):
        dirs[:] = [d for d in dirs if d != "node_modules"]
        for f in sorted(fs):
            p = os.path.join(dp, f)
            if f.endswith((".ts", ".tsx")) and "i18n.ts" not in p.replace("\\", "/"):
                out.append(p)
    return out


def keys_in(src: str) -> set[str]:
    return set(re.findall(r'(?<![\w$.])(?:t|tr)\("((?:[^"\\]|\\.)*)"\)', src))


def dictionary() -> set[str]:
    s = open(os.path.join(SRC, "i18n.ts"), encoding="utf-8").read()
    body = s[s.index("const EN"):]
    return set(re.findall(r'\n  "((?:[^"\\]|\\.)*)":', body))


def report() -> None:
    have = dictionary()
    rows, total, missing = [], 0, 0
    for p in files():
        src = open(p, encoding="utf-8").read()
        ks = keys_in(src)
        raw, n = wrap(src)
        total += len(ks)
        miss = {k for k in ks if k not in have}
        missing += len(miss)
        if n or miss:
            rows.append((n, len(miss), len(ks), os.path.relpath(p, ROOT)))
    rows.sort(reverse=True)
    print(f"{'oomslutna':>10} {'utan engelska':>14} {'nycklar':>8}  fil")
    for n, miss, ks, p in rows[:40]:
        print(f"{n:10d} {miss:14d} {ks:8d}  {p}")
    print(f"\nsumma: {sum(r[0] for r in rows)} strängar utan t(), {missing} nycklar utan engelsk rad, "
          f"{total} nycklar totalt")


def main(argv: list[str]) -> None:
    if "--rename" in argv:
        return rename()
    if "--report" in argv:
        return report()
    if "--keys" in argv:
        have = dictionary()
        seen: set[str] = set()
        for p in files():
            seen |= keys_in(open(p, encoding="utf-8").read())
        for k in sorted(seen - have):
            print(k)
        return
    targets = [a for a in argv if not a.startswith("--")]
    for rel in targets:
        p = rel if os.path.isabs(rel) else os.path.join(ROOT, rel)
        src = open(p, encoding="utf-8").read()
        out, n = wrap(src)
        if n:
            out = ensure_import(out, p)
            open(p, "w", encoding="utf-8").write(out)
        print(f"{n:5d}  {os.path.relpath(p, ROOT)}")


if __name__ == "__main__":
    main(sys.argv[1:])
