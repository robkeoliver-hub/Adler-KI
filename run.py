from adler import create_app
from waitress import serve


def main():
    app = create_app()
    # Both are validated server settings; network exposure remains loopback-only.
    serve(app, host=app.config['BIND_HOST'], port=app.config['PORT'], threads=4,
          connection_limit=32, channel_timeout=25, max_request_body_size=8192,
          clear_untrusted_proxy_headers=True)


if __name__ == '__main__':
    main()
