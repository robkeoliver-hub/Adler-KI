"""Run with venv Flask deps plus Playwright. Desktop engines, no real speech service."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import json
import argparse
from adler import create_app
from flask import render_template_string, request
from playwright.sync_api import sync_playwright, expect

origin='http://localhost'; prefix='/demo/ki-adler'
app=create_app(overrides={'TESTING':True,'DEMO_CODE':'synthetic-browser-code','PUBLIC_ORIGIN':origin})

@app.get('/fixture/<page>')
def portal_fixture(page):
 source=Path(__file__).with_name('fixtures').joinpath('portal_shell.html').read_text()
 return render_template_string(source + '<p id="fixture-page">{{ page }}</p><p id="fixture-value">{{ value }}</p>',page=page,value=request.args.get('value',''))


def run(engines):
 with sync_playwright() as p:
  for engine in engines:
   browser=getattr(p,engine).launch(headless=True)
   for width in [375,1280]:
    context=browser.new_context(viewport={'width':width,'height':1000})
    client=app.test_client();errors=[];pending={'hold':False,'route':None}
    def route_handler(route):
     req=route.request
     from urllib.parse import urlsplit
     url=urlsplit(req.url)
     if pending['hold'] and url.path==prefix+'/api/chat':
      pending['route']=route;return
     response=client.open(url.path+('?' + url.query if url.query else ''),method=req.method,data=req.post_data,headers={k:v for k,v in req.headers.items() if k.lower() not in ['cookie','content-length']})
     route.fulfill(status=response.status_code,headers={k:v for k,v in response.headers.items() if k.lower() not in ['set-cookie','content-length']},body=response.data)
    context.route('**/*',route_handler)
    context.add_init_script('''
    window.voiceCalls=0;window.speechCancels=0;window.micAborts=0;
    Object.defineProperty(window,'speechSynthesis',{value:{cancel(){window.speechCancels++;},getVoices(){return [];},speak(u){window.voiceCalls++;u.onstart?.();},speaking:false,pending:false}});
    window.SpeechRecognition=class {constructor(){window.testRecognition=this;}start(){this.onstart?.();}abort(){window.micAborts++;}};
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
    # Hiding while listening aborts microphone and returns focus to the toggle.
    page.locator('#mic').click();expect(page.locator('#mic')).to_have_attribute('aria-pressed','true')
    before=page.evaluate('window.micAborts')
    page.locator('[data-adler-toggle]').click()
    expect(page.locator('[data-adler-panel]')).to_be_hidden()
    expect(page.locator('[data-adler-toggle]')).to_be_focused()
    assert page.evaluate('window.micAborts')>before
    page.locator('[data-adler-toggle]').click()
    expect(page.locator('#mic')).to_have_attribute('aria-pressed','false')
    # Hiding during TTS cancels output; reopening never replays automatically.
    page.locator('#mic').click()
    page.evaluate("window.testRecognition.onresult({results:[Object.assign([{transcript:'Hallo Adler'}],{isFinal:true})]})")
    expect(page.locator('#status')).to_contain_text('spricht')
    spoken=page.evaluate('window.voiceCalls');before=page.evaluate('window.speechCancels')
    page.locator('[data-adler-toggle]').click()
    assert page.evaluate('window.speechCancels')>before
    page.locator('[data-adler-toggle]').click()
    assert page.evaluate('window.voiceCalls')==spoken
    # A delayed spoken-answer fetch cannot start audio after hide/reopen.
    pending['hold']=True
    page.locator('#mic').click()
    with page.expect_request('**/api/chat'):
     page.evaluate("window.testRecognition.onresult({results:[Object.assign([{transcript:'Erzähle etwas'}],{isFinal:true})]})")
    page.locator('[data-adler-toggle]').click()
    assert pending['route'] is not None
    pending['hold']=False
    try:pending['route'].fulfill(status=200,content_type='application/json',body=json.dumps({'reply':'SYNTHETIC-LATE-VOICE','mode':'mock'}))
    except Exception as exc:
     if 'already handled' not in str(exc) and 'closed' not in str(exc) and 'canceled' not in str(exc):raise
    page.locator('[data-adler-toggle]').click()
    page.locator('#message').fill('Danke');page.locator('#send').click();expect(page.locator('#send')).to_be_enabled()
    assert 'SYNTHETIC-LATE-VOICE' not in page.locator('#chat').inner_text()
    assert page.evaluate('window.voiceCalls')==spoken
    page.screenshot(path=str(Path(__file__).resolve().parent.parent/'docs'/f'preview-{engine}-{width}.png'),full_page=True)
    page.locator('#clear').click();page.locator('#login').wait_for(state='visible');assert page.locator('#chat').inner_text()==''
    assert not errors,errors
    print(engine,width,'PASS: login, local data, responsive, voice consent, hide stops mic/TTS, late answer discarded, text silent, logout')
    context.close()
   # Test-only host shell: existing navigation/forms work with companion on/off
   # and with JavaScript disabled. No replacement portal or real data endpoint.
   for javascript in [True,False]:
    context=browser.new_context(viewport={'width':375,'height':900},java_script_enabled=javascript)
    client=app.test_client();seen=[]
    def fixture_route(route):
     from urllib.parse import urlsplit
     req=route.request;url=urlsplit(req.url);seen.append(url.path)
     response=client.open(url.path+('?' + url.query if url.query else ''),method=req.method,headers={k:v for k,v in req.headers.items() if k.lower() not in ['cookie','content-length']})
     route.fulfill(status=response.status_code,headers={k:v for k,v in response.headers.items() if k.lower() not in ['set-cookie','content-length']},body=response.data)
    context.route('**/*',fixture_route)
    page=context.new_page();page.goto(origin+'/fixture/start')
    if javascript:
     expect(page.locator('[data-adler-panel]')).to_be_hidden()
     before=len(seen)
     page.locator('[data-adler-toggle]').click();expect(page.locator('[data-adler-panel]')).to_be_visible()
     assert len(seen)==before  # Toggle sends no API request.
     page.get_by_label('Begleiter-Testeingabe').focus();page.keyboard.press('Escape')
     expect(page.locator('[data-adler-panel]')).to_be_hidden();expect(page.locator('[data-adler-toggle]')).to_be_focused()
    for name,slug in [('Ergebnisse','ergebnisse'),('Abzeichen','abzeichen'),('Termine','termine'),('Start','start')]:
     page.get_by_role('link',name=name,exact=True).click();expect(page.locator('#fixture-page')).to_have_text(slug)
    if javascript:page.locator('[data-adler-toggle]').click()
    page.get_by_label('Vorhandenes Testformular').fill('synthetic-form-value')
    page.get_by_role('button',name='Testformular senden').click()
    expect(page.locator('#fixture-value')).to_have_text('synthetic-form-value')
    if not javascript:expect(page.locator('[data-adler-toggle]')).to_be_hidden()
    print(engine,'host fixture, JS='+str(javascript),'PASS: independent menus/forms, keyboard, optional companion')
    context.close()
   browser.close()
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--engines',nargs='+',default=['chromium','webkit']);run(parser.parse_args().engines)
