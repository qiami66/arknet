"""重签 16 条线路 + 生成全部客户端格式。跨平台，仅标准库。

  python3 refresh_all.py            重签全部账号名下的节点，验活后重写所有文件
  python3 refresh_all.py --check    不重签，只验证现有凭据并重写文件
  python3 refresh_all.py --list     列出节点与槽位分配
"""
import json, sys, base64, pathlib, urllib.parse, random, time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import client
import anytls_probe

API = 'https://zz11.qjfifnbotx.top:14215'
DB_PATH = HERE / 'nodes_full.json'
ACC_PATH = HERE / 'accounts.json'
OUT = HERE  # 生成物就放在同一目录（服务读这里）


def nd():
    return ''.join(random.choice('0123456789abcdef') for _ in range(32))


def retry(fn, tries=3, delay=1.5):
    """网络抖动兜底：失败重试，退避递增。"""
    last = None
    for i in range(tries):
        try:
            return fn()
        except Exception as e:
            last = e
            if i < tries - 1:
                time.sleep(delay * (i + 1))
    raise last


def login(email, pw):
    def once():
        st, t = client.call(API, '/api/v1/auth/login', 'POST',
                            {'identifier': email, 'password': pw}, device_id=nd())
        if st != 200:
            raise RuntimeError('login %s: %s' % (st, t[:120]))
        return json.loads(t)['data']['token']
    try:
        return retry(once), None
    except Exception as e:
        return None, str(e)


def mint(tok, node_id):
    def once():
        st, t = client.call(API, '/api/v1/nodes/connect', 'POST', {'nodeId': node_id}, token=tok)
        if st != 200:
            raise RuntimeError('connect %s: %s' % (st, t[:140]))
        return json.loads(t)['data']
    return retry(once)


def probe_retry(host, port, sni, pw):
    try:
        return retry(lambda: anytls_probe.probe(host, port, sni, pw), tries=3, delay=1.0)[0]
    except Exception:
        return False


def uri(n):
    q = urllib.parse.urlencode({'sni': n['sni'] or n['ingress'], 'insecure': '0'}, safe='')
    return 'anytls://%s@%s:%s/?%s#%s' % (n['password'], n['ingress'], n['port'], q,
                                         urllib.parse.quote(n['name']))


def q(s):
    return '"' + str(s).replace('\\', '\\\\').replace('"', '\\"') + '"'


def proxy_block(n, indent='  '):
    return [
        '%s- name: %s' % (indent, q(n['name'])),
        '%s  type: anytls' % indent,
        '%s  server: %s' % (indent, n['ingress']),
        '%s  port: %s' % (indent, n['port']),
        '%s  password: %s' % (indent, q(n['password'])),
        '%s  sni: %s' % (indent, q(n['sni'])),
        '%s  client-fingerprint: chrome' % indent,
        '%s  skip-cert-verify: false' % indent,
        '%s  udp: true' % indent,
    ]


def clash_yaml(nodes):
    L = ['# %d 条 AnyTLS 线路 - mihomo >= v1.18.6' % len(nodes),
         'mixed-port: 7890', 'allow-lan: false', 'mode: rule', 'log-level: info', 'ipv6: false',
         'external-controller: 127.0.0.1:9090', '', 'proxies:']
    for n in nodes:
        L += proxy_block(n)
    L += ['', 'proxy-groups:', '  - name: "PROXY"', '    type: select', '    proxies:', '      - "自动选择"']
    L += ['      - %s' % q(n['name']) for n in nodes]
    L += ['  - name: "自动选择"', '    type: url-test',
          '    url: "http://www.gstatic.com/generate_204"', '    interval: 300',
          '    tolerance: 50', '    lazy: false', '    proxies:']
    L += ['      - %s' % q(n['name']) for n in nodes]
    L += ['', 'rules:',
          '  - DOMAIN-SUFFIX,local,DIRECT',
          '  - IP-CIDR,127.0.0.0/8,DIRECT,no-resolve',
          '  - IP-CIDR,10.0.0.0/8,DIRECT,no-resolve',
          '  - IP-CIDR,172.16.0.0/12,DIRECT,no-resolve',
          '  - IP-CIDR,192.168.0.0/16,DIRECT,no-resolve',
          '  - GEOIP,CN,DIRECT',
          '  - MATCH,PROXY', '']
    return '\n'.join(L)


def flclash_yaml(nodes):
    L = ['# FlClash / mihomo 配置', 'mode: rule', 'log-level: info', 'ipv6: false', '',
         'dns:', '  enable: true', '  ipv6: false', '  listen: 0.0.0.0:1053',
         '  enhanced-mode: fake-ip', '  fake-ip-range: 198.18.0.1/16',
         '  nameserver:', '    - 223.5.5.5', '    - 119.29.29.29',
         '  fallback:', '    - 8.8.8.8', '    - 1.1.1.1', '', 'proxies:']
    for n in nodes:
        L += proxy_block(n)
    L += ['', 'proxy-groups:', '  - name: "PROXY"', '    type: select', '    proxies:', '      - "自动选择"']
    L += ['      - %s' % q(n['name']) for n in nodes]
    L += ['  - name: "自动选择"', '    type: url-test',
          '    url: "http://www.gstatic.com/generate_204"', '    interval: 300',
          '    tolerance: 50', '    lazy: false', '    proxies:']
    L += ['      - %s' % q(n['name']) for n in nodes]
    L += ['  - name: "全球直连"', '    type: select', '    proxies:', '      - DIRECT', '      - "PROXY"']
    L += ['', 'rules:',
          '  - DOMAIN-SUFFIX,local,DIRECT',
          '  - IP-CIDR,127.0.0.0/8,DIRECT,no-resolve',
          '  - IP-CIDR,10.0.0.0/8,DIRECT,no-resolve',
          '  - IP-CIDR,172.16.0.0/12,DIRECT,no-resolve',
          '  - IP-CIDR,192.168.0.0/16,DIRECT,no-resolve',
          '  - IP-CIDR,100.64.0.0/10,DIRECT,no-resolve',
          '  - GEOIP,CN,DIRECT',
          '  - MATCH,PROXY', '']
    return '\n'.join(L)


def verge_merge(nodes):
    L = ['# Clash Verge 全局扩展覆写配置（Merge）', 'prepend-proxies:']
    for n in nodes:
        L += proxy_block(n)
    L += ['', 'prepend-proxy-groups:', '  - name: "ARK 线路"', '    type: select', '    proxies:']
    L += ['      - %s' % q(n['name']) for n in nodes]
    L += ['      - DIRECT', '']
    return '\n'.join(L)


def write_outputs(db):
    live = [n for n in db['nodes'] if n.get('alive') and n.get('password')]
    uris = [uri(n) for n in live]
    blob = ('\n'.join(uris) + '\n') if uris else ''
    (OUT / 'shadowrocket_anytls_live.txt').write_text(blob, encoding='utf-8')
    (OUT / 'sub_live_base64.txt').write_text(base64.b64encode(blob.encode()).decode() + '\n', encoding='utf-8')
    (OUT / 'clash_config.yaml').write_text(clash_yaml(live), encoding='utf-8')
    (OUT / 'flclash_config.yaml').write_text(flclash_yaml(live), encoding='utf-8')
    (OUT / 'clash_verge_merge.yaml').write_text(verge_merge(live), encoding='utf-8')
    table = ['| # | 名称 | 入口 | 端口 | SNI | 账号 | 状态 |', '|---|---|---|---|---|---|---|']
    for n in db['nodes']:
        table.append('| %s | %s | %s | %s | %s | %s | %s |' % (
            n['idx'], n['name'], n['ingress'], n['port'], n['sni'], n.get('account'),
            '在线' if n.get('alive') else '失效'))
    (OUT / 'nodes_table.md').write_text('\n'.join(table) + '\n', encoding='utf-8')
    db['live_uris'] = uris
    DB_PATH.write_text(json.dumps(db, ensure_ascii=False, indent=1), encoding='utf-8')
    return live


def cmd_list():
    db = json.loads(DB_PATH.read_text(encoding='utf-8'))
    for n in db['nodes']:
        print('%02d %-8s %s:%s account=%s alive=%s' % (
            n['idx'], n['name'], n['ingress'], n['port'], n.get('account'), n.get('alive')))


def cmd_check():
    db = json.loads(DB_PATH.read_text(encoding='utf-8'))
    for n in db['nodes']:
        if not n.get('password'):
            n['alive'] = False
            continue
        ok = probe_retry(n['ingress'], n['port'], n['sni'] or n['ingress'], n['password'])
        n['alive'] = ok
        print('%-8s %s' % (n['name'], 'ALIVE' if ok else 'dead'))
    live = write_outputs(db)
    print('\n在线 %d/%d' % (len(live), len(db['nodes'])))


def cmd_refresh(only=None):
    db = json.loads(DB_PATH.read_text(encoding='utf-8'))
    accs = json.loads(ACC_PATH.read_text(encoding='utf-8'))['accounts']
    if only:
        accs = [a for a in accs if a['label'] == only]
    for n in db['nodes']:
        acc = n.get('account') or ''
        if '@' in acc:
            n['account'] = acc.split('@')[0]

    for acc in accs:
        mine = [n for n in db['nodes'] if n.get('account') == acc['label'] and n.get('nodeId')]
        if not mine:
            continue
        print('== %s (%d 条) ==' % (acc['label'], len(mine)))
        for n in mine:
            tok, raw = login(acc['email'], acc['password'])
            if not tok:
                print('  %-8s LOGIN FAIL %s' % (n['name'], raw[:90]))
                continue
            try:
                c = mint(tok, n['nodeId'])
            except Exception as e:
                print('  %-8s %s' % (n['name'], e))
                continue
            ok = probe_retry(c['ingress'], c['listenPort'],
                             c['tlsServerName'] or c['ingress'], c['password'])
            n.update({'port': c['listenPort'], 'sni': c['tlsServerName'], 'password': c['password'],
                      'proto': c['proto'], 'security': c['security'], 'alive': ok})
            print('  %-8s port=%s %s' % (n['name'], c['listenPort'], 'ALIVE' if ok else 'dead'))
            time.sleep(0.2)

    live = write_outputs(db)
    print('\n在线 %d/%d 端口=%s' % (len(live), len(db['nodes']),
                                   sorted(set(n['port'] for n in live)) or '-'))


if __name__ == '__main__':
    arg = sys.argv[1] if len(sys.argv) > 1 else ''
    if arg == '--list':
        cmd_list()
    elif arg == '--check':
        cmd_check()
    elif arg == '--account':
        cmd_refresh(only=sys.argv[2] if len(sys.argv) > 2 else None)
    else:
        cmd_refresh()
