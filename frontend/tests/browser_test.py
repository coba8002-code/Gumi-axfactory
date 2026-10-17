"""Real Chromium IndexedDB/offline shell test with deterministic mock API."""
import functools
import http.server
import json
from pathlib import Path
import threading
from playwright.sync_api import sync_playwright

root=Path(__file__).resolve().parents[1]
server=http.server.ThreadingHTTPServer(("127.0.0.1",0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(root)))
threading.Thread(target=server.serve_forever,daemon=True).start()
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        context=browser.new_context(viewport={"width":1024,"height":1366})
        received=[]
        state={"offline":False}
        def route(r):
            if state["offline"]:
                r.abort("internetdisconnected")
                return
            path=r.request.url.split("/api")[1]
            if path=="/me":data={"id":"u","tenant_id":"t","factory_id":"f","role":"worker"}
            elif path=="/equipment":data=[{"id":"00000000-0000-0000-0000-000000000001","name":"CNC-01"}]
            elif r.request.method=="GET":data=[]
            else:received.append(r.request.post_data_json);data=r.request.post_data_json
            r.fulfill(status=200,content_type="application/json",body=json.dumps(data))
        context.route("**/api/**",route)
        page=context.new_page()
        page.on("pageerror",lambda e:print("BROWSER ERROR:",e,flush=True))
        page.goto(f"http://127.0.0.1:{server.server_port}")
        page.fill("#token","test-only-token");page.click("#login-form button")
        page.wait_for_selector("#workspace",state="visible")
        page.evaluate("navigator.serviceWorker.ready")
        page.reload()
        page.wait_for_selector("#workspace",state="visible")
        page.wait_for_function("document.querySelector('#equipment').options.length===1 && !document.querySelector('#sync').disabled")
        state["offline"]=True
        context.set_offline(True)
        page.fill("#notes","공구 마모 오프라인");page.fill("#action","공구 교체");page.fill("#outcome","재가동 확인")
        page.click("#incident-form button")
        page.wait_for_function("document.querySelector('#queue').children.length===1")
        # Durable record survives page reload; shell is served by the service worker.
        page.reload()
        page.wait_for_selector("#workspace",state="visible")
        page.wait_for_function("document.querySelector('#queue').children.length===1")
        page.screenshot(path=str(root/"tests"/"tablet.png"),full_page=True)
        state["offline"]=False
        context.set_offline(False)
        page.click("#sync")
        page.wait_for_function("document.querySelector('#queue').children.length===0")
        assert any(x.get("notes")=="공구 마모 오프라인" for x in received),received
        assert any(x.get("action")=="공구 교체" for x in received),received
        page.click("#logout")
        assert page.locator("#workspace").is_hidden()
        browser.close()
        print("PASS: tablet login, IndexedDB offline save/reload, reconnect sync, logout")
finally:
    server.shutdown()
