"""Run with venv Flask deps plus Playwright. Desktop engines, no real speech service."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import json
import argparse
from adler import create_app
from playwright.sync_api import sync_playwright, expect

origin='http://localhost'; prefix='/demo/ki-adler'
app=create_app(overrides={'TESTING':True,'DEMO_CODE':'synthetic-browser-code','PUBLIC_ORIGIN':origin})

def run(engines):
 with sync_playwright() as p:
  for engine in engines:
   browser=getattr(p,engine).launch(headless=True)
   for width in [375,1280]:
    context=browser.new_context(viewport={'width':width,'height':1000})
    client=app.test_client();errors=[]
    def route_handler(route):
     req=route.request
     from urllib.parse import urlsplit
     url=urlsplit(req.url)
     response=client.open(url.path+('?' + url.query if url.query else ''),method=req.method,data=req.post_data,headers={k:v for k,v in req.headers.items() if k.lower() not in ['cookie','content-length']})
     route.fulfill(status=response.status_code,headers={k:v for k,v in response.headers.items() if k.lower() not in ['set-cookie','content-length']},body=response.data)
    context.route('**/*',route_handler)
    context.add_init_script('''
    window.voiceCalls=0;
    Object.defineProperty(window,'speechSynthesis',{value:{cancel(){},getVoices(){return [];},speak(u){window.voiceCalls++;u.onstart?.();},speaking:false,pending:false}});
    window.SpeechRecognition=class {constructor(){window.testRecognition=this;}start(){this.onstart?.();}abort(){}};
    ''')
    page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(origin+prefix+'/');page.locator('#code').fill('synthetic-browser-code');page.locator('#login button').click();page.locator('#controls').wait_for(state='visible')
    page.get_by_role('button',name='Meine Entwicklung').click();page.get_by_text('6 Ringe mehr',exact=False).wait_for()
    assert page.locator('#chat').inner_text().count('171')>=1
    assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
    page.locator('#mic').click();assert page.locator('#error').inner_text()
    page.locator('#message').fill('<img src=x onerror=alert(1)>');page.locator('#send').click();expect(page.locator('#send')).to_be_enabled()
    assert page.locator('#chat img').count()==0
    assert page.evaluate('window.voiceCalls')==0
    page.locator('#speech-consent').check();page.locator('#tts-consent').check();page.locator('#mic').click()
    expect(page.locator('#mic')).to_have_attribute('aria-pressed','true')
    page.evaluate("window.testRecognition.onresult({results:[Object.assign([{transcript:'Hallo Adler'}],{isFinal:true})]})")
    expect(page.locator('#status')).to_contain_text('spricht')
    assert page.evaluate('window.voiceCalls')==1
    page.locator('#stop').click();expect(page.locator('#mic')).to_have_attribute('aria-pressed','false')
    page.locator('#message').fill('Danke');page.locator('#send').click();expect(page.locator('#send')).to_be_enabled()
    assert page.evaluate('window.voiceCalls')==1
    page.screenshot(path=str(Path(__file__).resolve().parent.parent/'docs'/f'preview-{engine}-{width}.png'),full_page=True)
    page.locator('#clear').click();page.locator('#login').wait_for(state='visible');assert page.locator('#chat').inner_text()==''
    assert not errors,errors
    print(engine,width,'PASS: login, local data, responsive, voice consent, simulated speech, stop, text silent, safe text, logout')
    context.close()
   browser.close()
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--engines',nargs='+',default=['chromium','webkit']);run(parser.parse_args().engines)
