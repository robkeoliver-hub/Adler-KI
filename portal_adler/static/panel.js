(() => {
  'use strict';
  const root = document.getElementById('portal-adler');
  if (!root) return;
  const el = s => root.querySelector(s), panel = el('section');
  const base = root.dataset.api.replace(/\/session$/, '');
  let generation=0, controller, pending=false, ready=false, last='', recognition, expiry, binding='', speechGeneration=0;
  const state = s => { root.dataset.state=s; el('[data-mic]').setAttribute('aria-pressed',s==='listening'?'true':'false'); };
  const status = text => { el('[data-status]').textContent=text; };
  function line(text, speaker='adler', source='') {
    const log=el('[data-chat]'), p=document.createElement('p'); p.textContent=text; p.dataset.speaker=speaker;
    if (source) { const small=document.createElement('small');small.textContent=source; p.append(small); }
    log.append(p);while(log.children.length>12)log.firstChild.remove();log.scrollTop=log.scrollHeight;
  }
  function stop() {
    speechGeneration++;
    if(recognition){const r=recognition;recognition=null;r.onresult=r.onerror=r.onend=r.onstart=null;try{r.abort();}catch(_){}}
    window.speechSynthesis?.cancel();state('idle');status('Mikrofon aus · bereit für dich');
  }
  async function api(path,value,signal) {
    const response=await fetch(base+path,{method:'POST',credentials:'same-origin',signal,headers:{'Content-Type':'application/json','X-CSRF-Token':root.dataset.csrf,'X-Adler-Binding':binding},body:JSON.stringify(value),cache:'no-store'});
    if(!response.ok)throw Error(response.status===401?'Dein Zugang ist abgelaufen. Bitte KI-Adler erneut öffnen.':response.status===429?'Kurze Verschnaufpause! Bitte versuche es gleich noch einmal.':'Die Anfrage ist gerade nicht verfügbar. Dein Portalmenü funktioniert weiter.');
    return response.json();
  }
  function voices() {
    const select=el('[data-voice]'), previous=select.value;
    select.replaceChildren(new Option('Systemstimme',''));
    (window.speechSynthesis?.getVoices()||[]).filter(v=>/^de(?:[-_]|$)/i.test(v.lang)).forEach(v=>select.add(new Option(v.name,v.voiceURI)));
    select.value=previous;
  }
  function speak(text) {
    if(!window.speechSynthesis||!window.SpeechSynthesisUtterance){status('Vorlesen hier nicht verfügbar. Deine Antwort bleibt sichtbar.');return;}
    stop();const mine=speechGeneration,u=new SpeechSynthesisUtterance(text);u.lang='de-DE';u.rate=.95;
    const all=speechSynthesis.getVoices().filter(v=>/^de(?:[-_]|$)/i.test(v.lang));
    const choice=all.find(v=>v.voiceURI===el('[data-voice]').value)||all.find(v=>/Stefan|Markus|Martin|Hans|Conrad|Florian/i.test(v.name))||all[0];
    if(choice)u.voice=choice;
    u.onstart=()=>{if(mine===speechGeneration){state('speaking');status('KI-Adler spricht · Stopp beendet das Vorlesen');}};
    u.onend=()=>{if(mine===speechGeneration){state('idle');status('Mikrofon aus · für die nächste Frage auf Sprechen tippen');}};
    u.onerror=()=>{if(mine===speechGeneration){state('calm');status('Vorlesen blockiert. Tippe auf Vorlesen, um es erneut zu versuchen.');}};
    speechSynthesis.speak(u);
  }
  async function ask(value,spoken=false) {
    if(pending||panel.hidden)return;
    stop();pending=true;const mine=generation;controller=new AbortController();state('thinking');status('Einen Augenblick …');
    try {
      if(!ready){
        const match=location.pathname.slice((root.dataset.prefix||'').length).match(/^\/(?:jugend|erwachsen)\/([^/]+)(?:\/|$)/);
        if(!match)throw Error('Bitte dein persönliches Portal über deinen QR-Zugang öffnen.');
        const s=await api('/session',{token:decodeURIComponent(match[1])},controller.signal);
        if(mine!==generation)return;binding=s.binding;ready=true;
        clearTimeout(expiry);expiry=setTimeout(close,Math.min(s.expires_in,900)*1000);
      }
      const result=await api(value.tool?'/tool':'/chat',value,controller.signal);
      if(mine!==generation||panel.hidden)return;
      last=result.answer;
      const source={portal:'Aus deinem Vereinsportal',model:'KI-Antwort · kann Fehler enthalten',local:'Begrüßung',unavailable:'Freies Gespräch noch nicht verfügbar',consent_required:'Freigabe erforderlich'}[result.source]||'';
      line(last,'adler',source);state('idle');status('Mikrofon aus · bereit für dich');
      if(spoken)speak(last);
    }catch(error){if(mine===generation&&error.name!=='AbortError'){ready=false;line(error.message);state('calm');status('Mikrofon aus');}}
    finally{if(mine===generation)pending=false;}
  }
  function question(text,spoken=false){if(pending)return;line(text,'you');ask({text,external_consent:!!el('[data-external-consent]')?.checked},spoken);}
  function close() {
    generation++;clearTimeout(expiry);controller?.abort();pending=false;ready=false;stop();last='';
    el('[data-chat]').replaceChildren();el('[data-question]').value='';
    root.querySelectorAll('input[type=checkbox]').forEach(c=>{if(c.hasAttribute('data-motion'))return;c.checked=false;});
    panel.hidden=true;el('[data-open]').hidden=false;el('[data-open]').setAttribute('aria-expanded','false');
    api('/close',{}).catch(()=>{});binding='';el('[data-open]').focus();
  }
  el('[data-open]').addEventListener('click',()=>{panel.hidden=false;el('[data-open]').hidden=true;el('[data-open]').setAttribute('aria-expanded','true');expiry=setTimeout(close,900000);state('idle');el('[data-close]').focus();});
  el('[data-close]').addEventListener('click',close);
  el('[data-dismiss]').addEventListener('click',()=>{close();root.hidden=true;});
  el('[data-large]').addEventListener('click',()=>{const large=root.dataset.large!=='true';root.dataset.large=String(large);el('[data-large]').setAttribute('aria-pressed',String(large));});
  root.addEventListener('keydown',e=>{if(e.key==='Escape'&&!panel.hidden)close();});
  root.querySelectorAll('[data-tool]').forEach(b=>b.addEventListener('click',()=>{line(b.textContent,'you');ask({tool:b.dataset.tool});}));
  el('form').addEventListener('submit',e=>{e.preventDefault();const text=el('[data-question]').value.trim();if(text&&!pending){el('[data-question]').value='';question(text);}});
  el('[data-stop]').addEventListener('click',()=>{generation++;controller?.abort();pending=false;stop();});
  el('[data-replay]').addEventListener('click',()=>{if(last&&!panel.hidden)speak(last);});
  el('[data-motion]').addEventListener('change',e=>{root.dataset.motion=String(e.target.checked);});
  el('[data-speech-consent]').addEventListener('change',()=>{if(!el('[data-speech-consent]').checked)stop();});
  const Recognition=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!Recognition){el('[data-mic]').disabled=true;status('Spracheingabe hier nicht verfügbar · bitte tippen oder Tastatur-Diktat nutzen');}
  else el('[data-mic]').addEventListener('click',()=>{
    if(recognition){stop();return;}if(pending)return;
    if(!el('[data-speech-consent]').checked){el('details').open=true;status('Bitte zuerst die freiwillige Spracheingabe erlauben. Du kannst auch tippen.');return;}
    stop();const mine=generation;let failed=false;const r=new Recognition();recognition=r;r.lang='de-DE';r.continuous=false;r.interimResults=false;
    r.onstart=()=>{if(recognition===r){state('listening');status('Ich höre zu · erneut tippen beendet das Mikrofon');}};
    r.onresult=e=>{if(mine===generation&&!panel.hidden){const text=e.results?.[0]?.[0]?.transcript?.slice(0,300);if(text)question(text,true);}};
    r.onerror=e=>{failed=true;state('calm');status(e.error==='not-allowed'?'Mikrofonzugriff verweigert. Du kannst weiterhin tippen.':'Spracheingabe nicht verfügbar. Bitte tippen oder Tastatur-Diktat nutzen.');};
    r.onend=()=>{if(recognition===r)recognition=null;if(!failed&&!pending){state('idle');status('Mikrofon aus');}};
    try{r.start();}catch(_){recognition=null;state('calm');status('Mikrofon nicht verfügbar. Bitte tippen.');}
  });
  voices();window.speechSynthesis?.addEventListener?.('voiceschanged',voices);
  document.addEventListener('visibilitychange',()=>{if(document.hidden&&!panel.hidden)close();});
  window.addEventListener('pagehide',()=>{generation++;controller?.abort();stop();});
})();
