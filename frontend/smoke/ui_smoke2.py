"""The pages the first smoke never reached: the project analysis, the admin, the academy drills.

Same idea as ui_smoke.py - click everything with the console open and report what it said - on the parts of the
application that were built after that script was written. Run against serve_seeded.py on 127.0.0.1:8077.

The seeded user is made admin here, straight in the database, because that is the only way to be one: the role
comes from the server and never from anything the browser can say.
"""
import asyncio, os, sys
from playwright.async_api import async_playwright
SP = os.environ.get("SP", os.path.dirname(os.path.abspath(__file__)))
job, tok = open(f"{SP}/ui/job.txt").read().split()
BASE = "http://127.0.0.1:8077"
errs: list[str] = []
found: list[str] = []


def note(label):
    if errs:
        found.append(f"{label}: {errs[-1][:220]}")
        print(f"  !! {label}: {errs[-1][:220]}")
        errs.clear()


async def click_all(pg, sel, label, limit=30):
    n = await pg.locator(sel).count()
    for i in range(min(n, limit)):
        el = pg.locator(sel).nth(i)
        try:
            if not await el.is_visible():
                continue
            t = (await el.inner_text())[:28].replace("\n", " ")
            await el.click(timeout=2500)
            await pg.wait_for_timeout(320)
            note(f"{label} «{t}»")
        except Exception as e:
            print(f"  (kunde inte klicka {label} #{i}: {str(e)[:70]})")


async def main():
    async with async_playwright() as p:
        exe = os.environ.get("CHROME") or "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
        b = await p.chromium.launch(executable_path=exe if os.path.exists(exe) else None)
        ctx = await b.new_context(viewport={"width": 1500, "height": 940})
        pg = await ctx.new_page()
        pg.on("pageerror", lambda e: errs.append(f"pageerror: {e}"))
        pg.on("console", lambda m: errs.append(f"console.error: {m.text}") if m.type == "error" else None)
        # ett anrop som svarar med fel är också ett fynd, även när sidan i sig inte kraschar
        pg.on("response", lambda r: errs.append(f"http {r.status} {r.url.split('8077')[-1]}")
              if r.status >= 400 and "/api/" in r.url else None)

        # rollen kommer från servern och aldrig från webbläsaren, så den sätts där den bor: i lagret
        import glob, sqlite3
        dbs = sorted(glob.glob("/tmp/ui-*/ui.db"), key=os.path.getmtime)
        assert dbs, "hittar inte den seedade tjänstens lager"
        cx = sqlite3.connect(dbs[-1]); cx.execute("UPDATE users SET role='admin'"); cx.commit(); cx.close()

        await pg.goto(f"{BASE}/login", wait_until="networkidle")
        await pg.evaluate(f"localStorage.setItem('vvs_token', '{tok}')")

        print("== projektet: knappen till projektanalysen ==")
        await pg.goto(f"{BASE}/projekt", wait_until="networkidle"); await pg.wait_for_timeout(800)
        await pg.locator("a.ttl, .item a").first.click(); await pg.wait_for_timeout(900)
        note("öppna projektet")
        pid = pg.url.rstrip("/").split("/")[-1]
        await pg.get_by_role("button", name="Analysera projektet").click(); await pg.wait_for_timeout(900)
        note("till projektanalysen")
        assert pg.url.endswith("/analys"), pg.url

        print("== projektanalysen: valet, läsningen, flikarna, en rättelse ==")
        await pg.get_by_role("button", name="Välj projektanalys").click(); await pg.wait_for_timeout(1000)
        note("välj projektanalys")
        await pg.get_by_role("button", name="Läs handlingen").click()
        for _ in range(60):
            await pg.wait_for_timeout(500)
            if await pg.locator(".tabs button", has_text="Handlingar").count():
                break
        note("läs handlingen")
        await click_all(pg, ".tabs button", "pa-flik")
        await pg.locator(".tabs button", has_text="Handlingar").click(); await pg.wait_for_timeout(500)
        fix = pg.get_by_role("button", name="Rätta", exact=True)
        if await fix.count():
            await fix.first.click(); await pg.wait_for_timeout(400)
            await pg.locator(".pa-fix select").select_option("building")
            await pg.locator(".pa-fix input").first.fill("B")
            await pg.locator(".pa-fix button", has_text="Rätta").click(); await pg.wait_for_timeout(900)
            note("rätta huset")
            stale = await pg.locator(".pa-stale").count()
            print(f"  rättelse sparad · bannern 'läs om' visas: {bool(stale)}")
            if stale:
                await pg.locator(".pa-stale button").click()
                # bannern försvinner i samma ögonblick som omläsningen STARTAR - att vänta på den är att läsa
                # sidan innan svaret kommit. Vänta på det som faktiskt betyder klar: trädet ritas om med huset.
                for _ in range(80):
                    await pg.wait_for_timeout(500)
                    if "Hus B" in await pg.inner_text("body"):
                        break
                note("läs om efter rättelse")
                body = await pg.inner_text("body")
                print(f"  efter omläsning: hus B i trädet: {'Hus B' in body}")
                if "Hus B" not in body:
                    found.append("rättelsen till hus B syns inte i trädet efter omläsning")
        else:
            print("  (ingen Rätta-knapp: inga blad med id?)")
        await pg.locator(".tabs button", has_text="Före / efter").click(); await pg.wait_for_timeout(500)
        note("före/efter-fliken")
        await pg.locator(".tabs button", has_text="Mängder").click(); await pg.wait_for_timeout(500)
        note("mängder-fliken")
        body = await pg.inner_text("body")
        print(f"  mängder per hus visas: {'Horisontellt' in body}")
        if "Horisontellt" not in body:
            found.append("mängdfliken visar inga mängder trots två färdiga läsningar")

        print("== akademin: övningarna och framstegen på kontot ==")
        await pg.goto(f"{BASE}/lar", wait_until="networkidle"); await pg.wait_for_timeout(900)
        note("akademin")
        n = await pg.locator(".lf-drills .lx").count()
        print(f"  {n} övningar synliga")
        await click_all(pg, ".lf-drills button", "övningsknapp", limit=25)
        # ett steg i guiden, och sedan en omladdning: framsteget ska komma från kontot, inte bara från lagret
        await pg.get_by_role("button", name="Starta guiden").click(); await pg.wait_for_timeout(700)
        opt = pg.locator(".wz-quiz-opts button").first
        if await opt.count():
            await opt.click(); await pg.wait_for_timeout(200)
        await pg.locator(".wz-foot button", has_text="Nästa").click(); await pg.wait_for_timeout(500)
        await pg.keyboard.press("Escape"); await pg.wait_for_timeout(500)
        note("ett steg i guiden")
        await pg.evaluate("localStorage.removeItem('vvs.learn')")     # glöm det lokala: bara kontot är kvar
        await pg.goto(f"{BASE}/lar", wait_until="networkidle"); await pg.wait_for_timeout(1200)
        ring = await pg.locator(".lf-ring span").inner_text()
        print(f"  framsteg efter att det lokala lagret rensats: {ring.strip().replace(chr(10), '')}")
        note("framsteg från kontot")

        print("== admin: varje flik och varje knapp ==")
        await pg.goto(f"{BASE}/admin", wait_until="networkidle"); await pg.wait_for_timeout(1000)
        note("admin")
        tabs = await pg.locator(".adm-tabs button").count()
        print(f"  {tabs} flikar")
        for i in range(tabs):
            t = pg.locator(".adm-tabs button").nth(i)
            name = (await t.inner_text()).strip()
            await t.click(); await pg.wait_for_timeout(700)
            note(f"admin-flik {name}")
            # varje knapp som inte är destruktiv på fliken
            btns = pg.locator("main button:not(.adm-tabs button)")
            m = await btns.count()
            for k in range(min(m, 12)):
                bt = btns.nth(k)
                try:
                    if not await bt.is_visible():
                        continue
                    label = (await bt.inner_text()).strip()[:24]
                    if any(w in label.lower() for w in ("ta bort", "radera", "makulera")):
                        continue
                    await bt.click(timeout=2000); await pg.wait_for_timeout(350)
                    note(f"admin {name} «{label}»")
                    # stäng en eventuell dialog/prompt-rest
                    await pg.keyboard.press("Escape")
                except Exception:
                    pass
        # partnerformuläret hela vägen: ny partner, spara, betala ut
        await pg.locator(".adm-tabs button", has_text="Partners").click(); await pg.wait_for_timeout(600)
        np_ = pg.get_by_role("button", name="Ny partner")
        if await np_.count():
            await np_.click(); await pg.wait_for_timeout(300)
            fields = pg.locator(".adm-form input")
            await fields.nth(0).fill("Anna Rök"); await fields.nth(1).fill("anna@rok.se")
            await pg.locator(".adm-form input[placeholder='ANNA10']").fill("ANNA10")
            await pg.get_by_role("button", name="Spara", exact=True).click(); await pg.wait_for_timeout(900)
            note("spara partner")
            body = await pg.inner_text("body")
            print(f"  partnern syns i listan: {'Anna Rök' in body}")

        print(f"\nSIDAN LEVER: {len((await pg.inner_text('body')).strip()) > 200}")
        print(f"FYND: {len(found)}")
        for f in found:
            print("  -", f)
        await b.close()
        sys.exit(1 if found else 0)
asyncio.run(main())
