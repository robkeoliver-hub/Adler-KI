"""Synthetic browser integration; no real speech provider or Pi accessed."""
import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
from test_portal_adapter import host, ORIGIN, TOKEN_A
from portal_adler.testing_mount import PREFIX, mount_isolated_test
from werkzeug.test import Client
from werkzeug.wrappers import Response


def run():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True, executable_path=os.environ.get("CHROMIUM_EXECUTABLE"))
        for width,prefix in ((375,''),(1280,''),(375,PREFIX),(1280,PREFIX)):
            fixture=host.__wrapped__();app,*_=next(fixture);client=app.test_client();errors=[]
            if prefix:
                app.config['ADLER_ISOLATED_TEST']=True
                client=Client(mount_isolated_test(app),Response)
            context=browser.new_context(viewport={'width':width,'height':900})
            def handler(route):
                req=route.request;url=urlsplit(req.url)
                response=client.open(url.path,base_url=ORIGIN,method=req.method,data=req.post_data,
                    headers={k:v for k,v in req.headers.items() if k.lower() not in ('cookie','host','content-length')})
                route.fulfill(status=response.status_code,body=response.data,
                    headers={k:v for k,v in response.headers.items() if k.lower() not in ('set-cookie','content-length')})
            context.route('**/*',handler)
            context.add_init_script('''
                window.speaks=0;window.aborts=0;window.cancels=0;
                window.SpeechSynthesisUtterance=class{constructor(text){this.text=text;}};
                Object.defineProperty(window,'speechSynthesis',{value:{getVoices(){return [];},cancel(){window.cancels++;},speak(u){window.speaks++;u.onstart?.();}}});
                window.SpeechRecognition=class{constructor(){window.rec=this;}start(){this.onstart?.();}abort(){window.aborts++;}};
            ''')
            page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(ORIGIN+prefix+'/jugend/'+TOKEN_A)
            assert page.locator('nav a').get_attribute('href')=='/existing'
            page.locator('[data-open]').click()
            page.locator('[data-question]').fill('Mein letztes Ergebnis')
            page.locator('#portal-adler form button').click()
            page.get_by_text('101 Ringe',exact=False).wait_for()
            assert page.evaluate('window.speaks')==0
            page.locator('[data-replay]').click();assert page.evaluate('window.speaks')==1
            page.locator('[data-mic]').click()
            page.evaluate("window.rec.onresult({results:[[{transcript:'Nächster Termin'}]]})")
            page.get_by_text('Synthetic-Youth am',exact=False).wait_for()
            assert page.evaluate('window.speaks')==2
            page.locator('[data-mic]').click();before=page.evaluate('window.aborts')
            page.locator('[data-close]').click()
            assert page.evaluate('window.aborts')>before
            assert page.locator('section').is_hidden() and page.locator('[data-chat]').inner_text()==''
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            assert page.locator('nav a').get_attribute('href')=='/existing'
            page.locator('[data-open]').click();page.keyboard.press('Escape')
            assert page.locator('section').is_hidden()
            assert not errors, errors
            context.close()
            try:next(fixture)
            except StopIteration:pass
        # Unsupported recognition retains text controls.
        fixture=host.__wrapped__();app,*_=next(fixture);client=app.test_client()
        context=browser.new_context()
        context.route('**/*',handler)
        context.add_init_script('window.SpeechRecognition=undefined;window.webkitSpeechRecognition=undefined;')
        page=context.new_page();page.goto(ORIGIN+'/jugend/'+TOKEN_A);page.locator('[data-open]').click()
        assert page.locator('[data-mic]').is_disabled()
        page.locator('[data-tool="last_training"]').click();page.get_by_text('101 Ringe',exact=False).wait_for()
        context.close()
        try:next(fixture)
        except StopIteration:pass
        browser.close()
    print('Portal browser: root and mounted prefix, 375/1280, typed silent, replay, spoken input, stop/close, Escape, fallback and navigation passed')


if __name__=='__main__':run()
