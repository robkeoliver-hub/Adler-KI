"""Private test-only mount; never called by the production adapter."""
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.wrappers import Response

PREFIX = '/demo/ki-adler-portaltest'
COOKIE = 'ki_adler_portaltest_session'


def mount_isolated_test(app):
    if app.config.get('ADLER_ISOLATED_TEST') is not True:
        raise ValueError('Mount ist ausschließlich für die isolierte Testkopie erlaubt')
    if app.extensions.get('adler_test_mount'):
        raise ValueError('Testmount bereits vorbereitet')
    app.config.update(SESSION_COOKIE_NAME=COOKIE, SESSION_COOKIE_PATH=PREFIX+'/',
                      SESSION_COOKIE_DOMAIN=None, SESSION_COOKIE_SECURE=True,
                      SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax')
    app.extensions['adler_test_mount'] = True

    @app.after_request
    def no_cache(response):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Referrer-Policy'] = 'no-referrer'
        return response

    def fallback(environ, start_response):
        # Retains local start/stop controller's synthetic health check; no portal
        # content at the unmounted root. Other paths outside PREFIX fail closed.
        ok = environ.get('PATH_INFO') == '/'
        return Response('ISOLIERTER PORTALTEST – HTTPS-Mount vorbereitet' if ok else 'Nicht gefunden',
                        status=200 if ok else 404,
                        headers={'Cache-Control':'no-store','Referrer-Policy':'no-referrer'})(environ,start_response)

    return DispatcherMiddleware(fallback, {PREFIX: app})
