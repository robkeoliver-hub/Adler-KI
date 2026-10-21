from adler import create_app
from waitress import serve

if __name__ == '__main__':
    # Loopback only; never automatically expose to the LAN or change the portal.
    serve(create_app(), host='127.0.0.1', port=5057, threads=4,
          connection_limit=32, channel_timeout=25, max_request_body_size=8192,
          clear_untrusted_proxy_headers=True)
