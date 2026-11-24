"""订阅服务：读 nodes_full.json 输出四种格式。不重签，热更新（文件变了下次请求就生效）。

  python3 sub_server.py            # 0.0.0.0:8080
  python3 sub_server.py 9000       # 换端口
"""
import json, base64, pathlib, sys, socket, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import refresh_all as R

PORT = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 8080


def load():
    db = json.loads((HERE / 'nodes_full.json').read_text(encoding='utf-8'))
    return [n for n in db['nodes'] if n.get('alive') and n.get('password')]


class Handler(BaseHTTPRequestHandler):
    server_version = 'arknet-sub/1.0'

    def do_GET(self):
        path = self.path.split('?')[0].rstrip('/') or '/'
        try:
            nodes = load()
        except Exception as e:
            return self.reply(500, '# %s\n' % e, None)
        if path == '/sub':
            body = base64.b64encode(('\n'.join(R.uri(n) for n in nodes) + '\n').encode()).decode() \
                if nodes else ''
            return self.reply(200, body, nodes)
        if path == '/plain':
            return self.reply(200, ('\n'.join(R.uri(n) for n in nodes) + '\n') if nodes else '', nodes)
        if path == '/clash':
            return self.reply(200, R.clash_yaml(nodes), nodes, 'text/yaml; charset=utf-8')
        if path == '/flclash':
            return self.reply(200, R.flclash_yaml(nodes), nodes, 'text/yaml; charset=utf-8')
        if path == '/health':
            return self.reply(200, json.dumps({'nodes': len(nodes), 'port': self.server.server_address[1]}), nodes,
                              'application/json')
        return self.reply(404, '# /sub /plain /clash /flclash /health (%d nodes)\n' % len(nodes), nodes)

    def reply(self, code, body, nodes=None, ctype='text/plain; charset=utf-8'):
        data = body.encode()
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Access-Control-Allow-Origin', '*')
        if nodes is not None:
            self.send_header('Subscription-Userinfo', 'upload=0; download=0; total=0; expire=0')
            self.send_header('Profile-Update-Interval', '12')
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        print('[sub] %s %s' % (self.address_string(), fmt % args), flush=True)


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('223.5.5.5', 80))
        return s.getsockname()[0]
    except Exception:
        return '127.0.0.1'
    finally:
        s.close()


def serve(host='0.0.0.0', port=PORT):
    n = len(load())
    print('订阅服务启动，%d 条在线' % n, flush=True)
    print('  小火箭  http://%s:%s/sub' % (lan_ip(), port), flush=True)
    print('  Clash   http://%s:%s/clash' % (lan_ip(), port), flush=True)
    print('  FlClash http://%s:%s/flclash' % (lan_ip(), port), flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == '__main__':
    serve(port=PORT)
