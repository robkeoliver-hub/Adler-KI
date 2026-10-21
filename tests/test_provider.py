import io
import json
import urllib.error
import pytest
from adler.providers import CompatibleProvider, ProviderError

class Response(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self,*args): self.close()

def test_compatible_dialog_payload_and_bound(monkeypatch):
    captured={}
    class Opener:
        def open(self,req,timeout):
            captured.update(body=json.loads(req.data),headers=req.headers,timeout=timeout)
            return Response(json.dumps({'choices':[{'message':{'content':'Antwort'*200}}]}).encode())
    monkeypatch.setattr('urllib.request.build_opener',lambda *args:Opener())
    provider=CompatibleProvider('https://test.invalid/v1/chat/completions','model','private-key')
    result=provider.reply([{'role':'user','content':'Hallo'},{'role':'assistant','content':'Hi'},{'role':'user','content':'Und jetzt?'}])
    assert len(result)==1000
    assert captured['body']['messages'][-1]['content']=='Und jetzt?'
    assert captured['body']['messages'][0]['role']=='system'
    assert captured['body']['max_tokens']==160
    assert captured['timeout']==12
    assert captured['headers']['Authorization']=='Bearer private-key'

@pytest.mark.parametrize('body',[b'invalid',b'{}',b'x'*65537,b'{"choices":[{"message":{"content":null}}]}'])
def test_provider_invalid_response_safe(monkeypatch,body):
    class Opener:
        def open(self,*args,**kwargs): return Response(body)
    monkeypatch.setattr('urllib.request.build_opener',lambda *args:Opener())
    with pytest.raises(ProviderError,match='^provider unavailable$'):
        CompatibleProvider('https://test.invalid','model','secret').reply([])

def test_provider_timeout_safe_and_redirects_disabled(monkeypatch):
    captured=[]
    class Opener:
        def open(self,*args,**kwargs): raise TimeoutError('secret-personal-text')
    def factory(handler):
        captured.append(handler)
        return Opener()
    monkeypatch.setattr('urllib.request.build_opener',factory)
    with pytest.raises(ProviderError,match='^provider unavailable$'):
        CompatibleProvider('https://test.invalid','model','secret').reply([])
    assert captured[0].redirect_request(None,None,302,'',{},'https://other.invalid') is None
