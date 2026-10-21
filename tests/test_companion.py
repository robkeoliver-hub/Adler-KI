from pathlib import Path
from flask import render_template_string
from adler import create_app

P = '/demo/ki-adler'


def test_demo_wraps_existing_chat_and_retains_original_controls():
    app = create_app(overrides={'TESTING': True, 'PUBLIC_ORIGIN': 'http://localhost', 'DEMO_CODE': 'synthetic-companion-code'})
    client = app.test_client()
    response = client.get(P + '/')
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    for marker in ['data-adler-shell', 'data-adler-toggle', 'data-adler-panel', 'id="compose"', 'id="mic"', 'id="stop"', 'id="login"', 'id="clear"']:
        assert marker in html
    assert "script-src 'self'" in response.headers['Content-Security-Policy']
    for asset in ['companion.css', 'companion.js']:
        assert client.get(P + '/static/' + asset).status_code == 200


def test_macro_can_be_inserted_without_replacing_host_navigation():
    app = create_app(overrides={'TESTING': True, 'PUBLIC_ORIGIN': 'http://localhost', 'DEMO_CODE': 'synthetic-companion-code'})
    source = Path(__file__).with_name('fixtures').joinpath('portal_shell.html').read_text()
    with app.test_request_context():
        html = render_template_string(source)
    assert html.index('id="existing-nav"') < html.index('data-adler-shell')
    for name in ['Start', 'Ergebnisse', 'Abzeichen', 'Termine']:
        assert '>' + name + '</a>' in html
    assert 'action="/fixture/update"' in html
    assert 'aria-expanded="false"' in html
    assert 'data-adler-panel aria-label="KI-Adler Sprach- und Chatbegleiter" hidden' in html
