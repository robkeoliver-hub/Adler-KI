"""Local synthetic HTTP benchmark; never loads private config or the portal."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import json
import threading
import time
import statistics
import urllib.request
import http.cookiejar
from waitress import create_server
from adler import create_app

app=create_app(overrides={'TESTING':True,'DEMO_CODE':'synthetic-benchmark-code','PUBLIC_ORIGIN':'http://127.0.0.1:5058','CHAT_LIMIT':30})
server=create_server(app,host='127.0.0.1',port=5058,threads=2)
thread=threading.Thread(target=server.run,daemon=True);thread.start()
origin='http://127.0.0.1:5058';base=origin+'/demo/ki-adler/api/'
opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
def post(path,data,csrf=''):
 req=urllib.request.Request(base+path,data=json.dumps(data).encode(),headers={'Origin':origin,'Content-Type':'application/json','X-CSRF-Token':csrf})
 start=time.perf_counter()
 with opener.open(req,timeout=5) as r:value=json.load(r)
 return value,(time.perf_counter()-start)*1000
try:
 data,_=post('login',{'code':'synthetic-benchmark-code'});csrf=data['csrf']
 result={}
 for label,text in [('mock-dialog','Hallo Adler'),('local-data','Bin ich besser geworden?')]:
  times=[]
  for _ in range(12):
   data,ms=post('chat',{'message':text},csrf);assert data['reply'];times.append(ms)
  result[label]={'n':len(times),'median_ms':round(statistics.median(times),2),'p95_ms':round(sorted(times)[-1],2),'min_ms':round(min(times),2),'max_ms':round(max(times),2)}
 print(json.dumps({'environment':'Linux cloud executor, loopback HTTP, Waitress, synthetic mock; not Raspberry Pi or speech','results':result},indent=2))
finally:
 server.close()
