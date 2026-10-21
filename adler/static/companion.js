'use strict';
// Presentation only. No network, storage, account, consent or data access.
document.querySelectorAll('[data-adler-shell]').forEach(shell=>{
  const toggle=shell.querySelector('[data-adler-toggle]');
  const panel=shell.querySelector('[data-adler-panel]');
  if(!toggle||!panel)return;
  function setOpen(open){
    if(!open){
      // The chat controller cancels its own microphone, TTS and pending fetch.
      shell.dispatchEvent(new CustomEvent('adler:hide',{bubbles:true}));
    }
    panel.hidden=!open;
    toggle.setAttribute('aria-expanded',String(open));
    toggle.textContent=open?'KI-Adler ausblenden':'KI-Adler einblenden';
    if(!open)toggle.focus();
  }
  toggle.hidden=false;
  toggle.addEventListener('click',()=>setOpen(panel.hidden));
  shell.addEventListener('keydown',event=>{
    if(event.key==='Escape'&&!panel.hidden&&panel.contains(event.target)){
      event.preventDefault();setOpen(false);
    }
  });
});
