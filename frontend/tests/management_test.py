"""Management navigation/actions against deterministic fixtures; DB isolation tested separately."""
import functools
import http.server
import json
from pathlib import Path
import threading
from datetime import datetime,timezone,timedelta
from playwright.sync_api import sync_playwright

root=Path(__file__).resolve().parents[1]
server=http.server.ThreadingHTTPServer(("127.0.0.1",0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(root)))
threading.Thread(target=server.serve_forever,daemon=True).start()
now=datetime.now(timezone.utc)
eq={"id":"e1","name":"CNC-01 · 가공 1라인"}
sensor={"id":"s1","name":"설비 전력계","equipment_id":"e1","equipment_name":eq["name"],
    "observed_at":now.isoformat(),"received_at":now.isoformat(),"metric":"power_kw","value":12.4,
    "unit":"kW","quality":"estimated","source":"simulator","stream_status":"recent"}
incident={"id":"i1","equipment_id":"e1","reason":"tool","notes":"공구 진동 점검","started_at":(now-timedelta(hours=1)).isoformat(),"approved":False}
accounts=[{"id":"u1","role":"admin","active":True},{"id":"u2","role":"worker","active":True},{"id":"d1","role":"device","active":True}]
posted=[]
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        context=browser.new_context(viewport={"width":1440,"height":1100})
        def route(r):
            path=r.request.url.split("/api",1)[1].split("?")[0]
            method=r.request.method
            if method=="POST":posted.append((path,r.request.post_data_json))
            if path=="/me":
                role="worker" if r.request.headers.get("authorization")=="Bearer worker" else "admin"
                data={"id":"u1","tenant_id":"t1","factory_id":"sample-factory","role":role}
            elif path=="/monitoring":
                data={"as_of":now.isoformat(),"equipment":[eq],"sensors":[sensor],
                    "summary":{"equipment":1,"sensors":1,"recent_streams":1,"attention_streams":0,"pending_incidents":1,"open_incidents":1}}
            elif path=="/monitoring/readings":
                data={"metric":"power_kw","points":[{"observed_at":(now-timedelta(minutes=12-i)).isoformat(),"value":10+i%5,
                    "quality":"estimated","source":"simulator","unit":"kW"} for i in range(12)]}
            elif path=="/incidents":data=[incident]
            elif path=="/incidents/i1":
                data={**incident,"ended_at":None,"actions":[{"action":"공구 교체","outcome":"정상 재가동"}]}
            elif path=="/incidents/i1/approve":
                incident["approved"]=True;data=incident
            elif path=="/management/identities":data=accounts
            elif path=="/management/identities/u2/deactivate":
                accounts[1]["active"]=False;data=accounts[1]
            elif path=="/sensors":data=[sensor]
            elif path=="/reports":data=[]
            elif path=="/knowledge":data={"answer":"승인 사례","sources":[],"limitations":["검색 예시"]}
            elif path=="/audit":data=[]
            else:data={"id":"new",**(r.request.post_data_json or {})}
            r.fulfill(status=200,content_type="application/json",body=json.dumps(data))
        context.route("**/api/**",route)
        page=context.new_page()
        page.goto(f"http://127.0.0.1:{server.server_port}/management/")
        page.fill("#token","admin");page.click("#login-form button")
        page.wait_for_selector("#chart svg")
        assert page.locator("#total-equipment").inner_text()=="1"
        assert "시뮬레이터" in page.locator("#streams").inner_text()
        for width,height,name in [(1440,1100,"management-desktop"),(390,844,"management-mobile")]:
            page.set_viewport_size({"width":width,"height":height})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"),name
            page.screenshot(path=str(root/"tests"/(name+".png")),full_page=True)
        page.set_viewport_size({"width":1440,"height":1100})
        page.click('[data-page="inventory"]')
        page.fill("#equipment-name","CNC-NEW");page.click("#equipment-form button")
        page.wait_for_function("document.querySelector('#status').textContent.includes('설비를 등록')")
        assert any(path=="/equipment" and data["name"]=="CNC-NEW" for path,data in posted)
        page.click('[data-page="incidents"]');page.click("#incident-rows button")
        page.wait_for_selector("#review-dialog[open]")
        assert "공구 교체" in page.locator("#review-detail").inner_text()
        page.fill("#review-evidence","현장 재가동 확인");page.check("#review-resolved")
        page.click("#approve-button")
        page.wait_for_function("!document.querySelector('#review-dialog').open")
        assert any(path=="/incidents/i1/approve" for path,_ in posted)
        page.click('[data-page="accounts"]')
        page.once("dialog",lambda dialog:dialog.accept())
        page.locator("#account-rows tr").filter(has_text="u2").locator("button").click()
        page.wait_for_function("document.querySelector('#status').textContent.includes('접근을 중지')")
        for section in ["knowledge","reports","audit"]:
            page.click('[data-page="'+section+'"]')
            assert page.locator("#"+section).is_visible()
        page.click("#logout")
        page.fill("#token","worker");page.click("#login-form button")
        page.wait_for_function("document.querySelector('#error').textContent.includes('전용')")
        assert page.locator("#dashboard").is_hidden()
        browser.close()
        print("PASS: management chart, responsive layout, equipment registration, approval, revocation, navigation and worker denial")
finally:
    server.shutdown()
