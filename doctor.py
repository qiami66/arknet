"""部署前自检：这台机器到底能不能跑这套东西。

  python3 doctor.py

检查项：python 版本、系统时钟偏差、API 可达性、节点端口连通性、现有凭据在线数。
"""
import sys, socket, ssl, json, pathlib, urllib.request, urllib.error, email.utils, datetime, time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

API_HOST = 'zz11.qjfifnbotx.top'
API_PORT = 14215
NODE_SAMPLE = ['noded1.gykisjdcth.top', 'noded9.gykisjdcth.top', 'noded16.gykisjdcth.top']
NODE_PORT = 10021

ok_all = True


def mark(ok, label, detail=''):
    global ok_all
    if not ok:
        ok_all = False
    print('%s %-26s %s' % ('[ OK ]' if ok else '[FAIL]', label, detail))


def check_python():
    v = sys.version_info
    mark(v >= (3, 7), 'python 版本', '%d.%d.%d' % (v[0], v[1], v[2]))


def api_touch():
    """发一个不带签名的请求，只为了探连通性和拿 Date 头。400/403 都算可达。"""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request('https://%s:%d/api/v1/communication-domains' % (API_HOST, API_PORT))
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=12) as r:
            return r.status, r.headers
    except urllib.error.HTTPError as e:
        return e.code, e.headers


def check_clock():
    try:
        code, headers = api_touch()
    except Exception as e:
        mark(False, 'API 时钟', '拿不到 Date 头：%r' % e)
        return
    date = headers.get('Date')
    if not date:
        mark(False, 'API 时钟', '响应没有 Date 头')
        return
    try:
        srv = email.utils.parsedate_to_datetime(date)
        now = datetime.datetime.now(datetime.timezone.utc)
        drift = abs((now - srv).total_seconds())
    except Exception as e:
        mark(False, 'API 时钟', '解析失败 %r' % e)
        return
    mark(drift < 300, '系统时钟偏差', '%.0f 秒（超过 300 秒接口签名会被拒）' % drift)


def check_api():
    try:
        code, _ = api_touch()
        mark(code in (200, 400, 403, 404), 'API 可达',
             'HTTP %s（400/403 是没签名的正常拒绝，说明服务在）' % code)
    except Exception as e:
        mark(False, 'API 可达', '%r' % e)


def check_nodes():
    good = 0
    for h in NODE_SAMPLE:
        t0 = time.time()
        try:
            s = socket.create_connection((h, NODE_PORT), timeout=10)
            s.close()
            good += 1
            print('[ OK ] 节点端口 %-16s %d 可达 %.0fms' % (h, NODE_PORT, (time.time() - t0) * 1000))
        except Exception as e:
            print('[ .. ] 节点端口 %-16s 这次没连上（%s）' % (h, type(e).__name__))
    # 单个节点抖动不算整体失败，3 个样本里过 2 个就算链路通
    mark(good >= 2, '节点链路', '%d/%d 个样本可达' % (good, len(NODE_SAMPLE)))


def check_creds():
    try:
        import anytls_probe as ap
        db = json.loads((HERE / 'nodes_full.json').read_text(encoding='utf-8'))
    except Exception as e:
        mark(False, '凭据检查', '读不到 nodes_full.json: %r' % e)
        return
    alive = 0
    for n in db['nodes']:
        if not n.get('password'):
            continue
        try:
            ok, _ = ap.probe(n['ingress'], n['port'], n['sni'] or n['ingress'], n['password'], timeout=8)
        except Exception:
            ok = False
        alive += 1 if ok else 0
    total = len(db['nodes'])
    mark(alive > 0, '现有凭据在线', '%d/%d（0 条就跑一次 refresh_all.py）' % (alive, total))


if __name__ == '__main__':
    print('=' * 60)
    print(' arknet 部署自检')
    print('=' * 60)
    check_python()
    check_api()
    check_clock()
    check_nodes()
    check_creds()
    print('=' * 60)
    if ok_all:
        print(' 全部通过，可以直接跑 run_all.py 或 install.sh')
    else:
        print(' 有项目失败，先按上面的报错排查再部署')
    print('=' * 60)
    sys.exit(0 if ok_all else 1)
