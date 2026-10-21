(() => {
  'use strict';
  const root = document.getElementById('portal-adler');
  if (!root) return;
  const el = s => root.querySelector(s), panel = el('section');
  const base = root.dataset.api.replace(/\/session$/, '');
  let generation = 0, controller, pending = false, ready = false, last = '', recognition, expiry, binding = '';
  const status = text => { el('[data-status]').textContent = text; };
  const line = text => {
    const log = el('[data-chat]'), p = document.createElement('p'); p.textContent = text;
    log.append(p); while (log.children.length > 12) log.firstChild.remove();
    p.scrollIntoView({block:'nearest'});
  };
  function stop() {
    if (recognition) { const r = recognition; recognition = null; r.onresult = r.onerror = r.onend = null; r.abort(); }
    window.speechSynthesis?.cancel(); status('Mikrofon aus');
  }
  async function api(path, value, signal) {
    const response = await fetch(base + path, {method:'POST', credentials:'same-origin', signal,
      headers:{'Content-Type':'application/json', 'X-CSRF-Token':root.dataset.csrf, 'X-Adler-Binding':binding}, body:JSON.stringify(value), cache:'no-store'});
    if (!response.ok) throw Error(response.status === 401 ? 'Sitzung abgelaufen. Bitte das Panel erneut öffnen.' : 'Die Anfrage ist gerade nicht verfügbar. Nutze bitte das normale Portalmenü.');
    return response.json();
  }
  function speak(text) {
    if (!window.speechSynthesis || !window.SpeechSynthesisUtterance) { status('Vorlesen nicht verfügbar. Die Textantwort bleibt sichtbar.'); return; }
    stop();
    const utterance = new SpeechSynthesisUtterance(text); utterance.lang = 'de-DE';
    const voices = speechSynthesis.getVoices().filter(v => /^de[-_]/i.test(v.lang));
    if (voices.length) utterance.voice = voices[0];
    utterance.onstart = () => status('KI-Adler spricht');
    utterance.onend = () => status('Mikrofon aus');
    utterance.onerror = () => status('Vorlesen nicht möglich. Tippe bei Bedarf erneut auf Vorlesen.');
    speechSynthesis.speak(utterance);
  }
  async function ask(tool, spoken=false) {
    if (pending || panel.hidden) return;
    stop(); pending = true; const mine = generation;
    controller = new AbortController(); status('Ich sehe im Portal nach …');
    try {
      if (!ready) {
        const match = location.pathname.slice((root.dataset.prefix || '').length).match(/^\/jugend\/([^/]+)(?:\/|$)/);
        if (!match) throw Error('Bitte dein persönliches Jugendportal öffnen.');
        const session = await api('/session', {token:decodeURIComponent(match[1])}, controller.signal);
        if (mine !== generation) return; binding = session.binding; ready = true;
      }
      const result = await api('/tool', {tool}, controller.signal);
      if (mine !== generation || panel.hidden) return;
      last = result.answer; line(last); status('Mikrofon aus');
      if (spoken) speak(last);
    } catch (error) {
      if (mine === generation && error.name !== 'AbortError') { ready = false; line(error.message); status('Mikrofon aus'); }
    } finally { if (mine === generation) pending = false; }
  }
  function question(text, spoken=false) {
    line(text);
    if (/letzte|ergebnis|geschossen|ringe/i.test(text)) ask('last_training', spoken);
    else if (/termin|nächste|naechste|wann.*training/i.test(text)) ask('next_event', spoken);
    else line('Diese Frage kann ich noch nicht frei beantworten. Nutze „Mein letztes Training“ oder „Nächster Jugendtermin“.');
  }
  function close() {
    generation++; clearTimeout(expiry); controller?.abort(); pending = false; ready = false; stop(); last = '';
    el('[data-chat]').replaceChildren(); el('[data-question]').value = '';
    panel.hidden = true; el('[data-open]').setAttribute('aria-expanded','false');
    api('/close', {}).catch(() => {}); binding = ''; el('[data-open]').focus();
  }
  el('[data-open]').addEventListener('click', () => {
    if (!panel.hidden) { close(); return; }
    panel.hidden = false; expiry = setTimeout(close, 15 * 60 * 1000); el('[data-open]').setAttribute('aria-expanded','true'); el('[data-question]').focus();
  });
  el('[data-close]').addEventListener('click', close);
  root.addEventListener('keydown', e => { if (e.key === 'Escape' && !panel.hidden) close(); });
  root.querySelectorAll('[data-tool]').forEach(b => b.addEventListener('click', () => ask(b.dataset.tool)));
  el('form').addEventListener('submit', e => { e.preventDefault(); const text = el('[data-question]').value.trim(); if (text && !pending) { el('[data-question]').value = ''; question(text); } });
  el('[data-stop]').addEventListener('click', () => { generation++;controller?.abort();pending=false;stop(); });
  el('[data-replay]').addEventListener('click', () => { if (last && !panel.hidden) speak(last); });
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Recognition) { el('[data-mic]').disabled = true; status('Spracherkennung hier nicht verfügbar. Bitte tippen.'); }
  else el('[data-mic]').addEventListener('click', () => {
    if (recognition) { stop();return; } if (pending) return;
    stop(); const mine = generation; let failed = false; recognition = new Recognition(); recognition.lang='de-DE'; recognition.continuous=false; recognition.interimResults=false;
    recognition.onstart = () => status('Mikrofon hört zu – erneut tippen zum Stoppen');
    recognition.onresult = e => { if (mine === generation && !panel.hidden) question(e.results[0][0].transcript.slice(0,300), true); };
    recognition.onerror = e => { failed = true; status(e.error === 'not-allowed' ? 'Mikrofonzugriff verweigert. Du kannst weiterhin tippen.' : 'Spracheingabe nicht verfügbar. Bitte tippen.'); };
    recognition.onend = () => { recognition = null; if (!failed && !pending) status('Mikrofon aus'); };
    try { recognition.start(); } catch (_) { recognition = null;status('Mikrofon nicht verfügbar. Bitte tippen.'); }
  });
  document.addEventListener('visibilitychange', () => { if (document.hidden && !panel.hidden) close(); });
  window.addEventListener('pagehide', () => { generation++;controller?.abort();stop(); });
})();
