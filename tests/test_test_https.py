"""Synthetic nginx and WSGI tests; no real nginx config is changed."""
import importlib.util
import re
from pathlib import Path

import pytest
from werkzeug.test import Client
from werkzeug.wrappers import Response

from portal_adler.testing_mount import PREFIX, COOKIE, mount_isolated_test
from test_portal_adapter import host, ORIGIN, TOKEN_A

spec=importlib.util.spec_from_file_location('preview',Path(__file__).resolve().parents[1]/'scripts/preview_test_proxy.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

SITE='''server {
 listen 80;
 server_name adlerzug.duckdns.org;
 location / { return 301 https://$host$request_uri; }
}
server {
 listen 443 ssl;
 server_name adlerzug.duckdns.org;
 # comment { must not open a block
 ssl_certificate /synthetic/cert.pem;
 location ^~ /demo/ki-adler/ { proxy_pass http://127.0.0.1:5057; }
 location / { proxy_pass http://127.0.0.1:5000; }
}
'''


def test_candidate_only_adds_specific_location():
    path,original,candidate=m.make_candidate({'/etc/nginx/sites-enabled/synthetic':SITE})
    assert original==SITE and candidate.replace(m.BLOCK,'',1)==SITE
    assert 'proxy_pass http://127.0.0.1:5071;' in candidate
    assert 'access_log off;' in candidate
    assert 'X-Forwarded-Proto $scheme' in candidate
    assert candidate.count('proxy_pass http://127.0.0.1:5000;')==1
    assert candidate.count('proxy_pass http://127.0.0.1:5057;')==1


@pytest.mark.parametrize('source', [
    SITE.replace('5057','5999'), SITE.replace('5000','5999'),
    SITE.replace('listen 443 ssl','listen 443'),SITE.replace('adlerzug.duckdns.org','other.example'),
    SITE+SITE, SITE.replace('ssl_certificate /synthetic/cert.pem;', 'include extra.conf;'),
    SITE.replace('location / { proxy_pass http://127.0.0.1:5000; }',m.BLOCK+'location / { proxy_pass http://127.0.0.1:5000; }'),
])
def test_ambiguous_or_different_topology_fails_closed(source):
    with pytest.raises(m.PreviewError):m.make_candidate({'/etc/nginx/sites-enabled/synthetic':source})


def test_quoted_comments_and_braces_do_not_change_structure():
    source=SITE.replace('ssl_certificate /synthetic/cert.pem;','set $test "# braces { } and ;";')
    assert m.make_candidate({'/etc/nginx/sites-enabled/synthetic':source})[2].replace(m.BLOCK,'',1)==source
    with pytest.raises(m.PreviewError):m.blocks(source+'}')


def test_dump_file_boundaries_and_no_console_source():
    dump='# configuration file /etc/nginx/nginx.conf:\nhttp { include sites-enabled/*; }\n\n# configuration file /etc/nginx/sites-enabled/synthetic:\n'+SITE
    files=m.split_dump(dump)
    assert m.make_candidate(files)[0]=='/etc/nginx/sites-enabled/synthetic'
    with pytest.raises(m.PreviewError):m.split_dump('arbitrary data')


def test_mounted_routes_cookie_scope_and_production_cookie_untouched(host):
    app=host[0];app.config['ADLER_ISOLATED_TEST']=True
    client=Client(mount_isolated_test(app),Response)
    client.set_cookie('session','synthetic-production-cookie',domain='portal.example')
    page=client.get(PREFIX+'/jugend/'+TOKEN_A,base_url=ORIGIN)
    assert page.status_code==200 and 'data-prefix="'+PREFIX+'"' in page.text
    assert PREFIX+'/ki-adler/static/panel.js' in page.text
    assert client.get_cookie('session',domain='portal.example').value=='synthetic-production-cookie'
    cookie=client.get_cookie(COOKIE,domain='portal.example',path=PREFIX+'/')
    assert cookie and cookie.secure and cookie.http_only
    csrf=re.search(r'data-csrf="([^"]+)"',page.text).group(1)
    headers={'Origin':ORIGIN,'X-CSRF-Token':csrf}
    bound=client.post(PREFIX+'/ki-adler/session',json={'token':TOKEN_A},headers=headers,base_url=ORIGIN)
    assert bound.status_code==200
    headers['X-Adler-Binding']=bound.json['binding']
    result=client.post(PREFIX+'/ki-adler/tool',json={'tool':'last_training'},headers=headers,base_url=ORIGIN)
    assert result.json['data']['score']==101
    assert result.headers['Cache-Control']=='no-store'
    assert client.get('/jugend/'+TOKEN_A,base_url=ORIGIN).status_code==404
    assert client.get('/demo/ki-adler/',base_url=ORIGIN).status_code==404
    assert client.get('/',base_url=ORIGIN).status_code==200


def test_mount_requires_explicit_isolated_flag(host):
    app=host[0]
    with pytest.raises(ValueError):mount_isolated_test(app)
    app.config['ADLER_ISOLATED_TEST']=True
    mount_isolated_test(app)
    with pytest.raises(ValueError):mount_isolated_test(app)


def test_nginx_empty_strings_and_braced_variables():
    source=SITE.replace('ssl_certificate /synthetic/cert.pem;', 'proxy_set_header Connection ""; set $value http://${host};')
    assert m.make_candidate({'/etc/nginx/sites-enabled/synthetic':source})[2].replace(m.BLOCK,'',1)==source
