"""把刷新产物同步到 Gitee（在 GitHub Actions 里跑）。

只需要环境变量 GITEE_TOKEN。
"""
import os, json, base64, time, pathlib, urllib.request, urllib.error

TK = os.environ.get('GITEE_TOKEN', '')
if not TK:
    raise SystemExit('缺 GITEE_TOKEN')

OWNER, REPO = 'qiami66', 'arknet'
HERE = pathlib.Path(__file__).resolve().parent
FILES = ['nodes_full.json', 'sub_live_base64.txt', 'clash_config.yaml',
         'flclash_config.yaml', 'nodes_table.md']


def api(path, method='GET', body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request('https://gitee.com/api/v5' + path, method=method, data=data,
        headers={'Content-Type': 'application/json;charset=UTF-8', 'User-Agent': 'arknet'})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', 'replace')[:200]


print('token 校验', api('/user?access_token=' + TK)[0])

for f in FILES:
    p = HERE / f
    if not p.exists():
        print('跳过（本地没有）', f)
        continue
    content = base64.b64encode(p.read_bytes()).decode()
    st, cur = api('/repos/%s/%s/contents/%s?access_token=%s' % (OWNER, REPO, f, TK))
    if st == 200 and isinstance(cur, dict) and cur.get('sha'):
        st2, r2 = api('/repos/%s/%s/contents/%s' % (OWNER, REPO, f), 'PUT',
                      {'access_token': TK, 'content': content, 'message': 'refresh ' + f,
                       'sha': cur['sha']})
        print('update %-28s %s' % (f, st2))
    else:
        st2, r2 = api('/repos/%s/%s/contents/%s' % (OWNER, REPO, f), 'POST',
                      {'access_token': TK, 'content': content, 'message': 'add ' + f})
        print('add    %-28s %s' % (f, st2))
    if st2 not in (200, 201):
        print('   ', r2)
    time.sleep(0.4)

# 验证 raw
st, body = 0, b''
try:
    with urllib.request.urlopen('https://gitee.com/%s/%s/raw/master/sub_live_base64.txt' % (OWNER, REPO), timeout=30) as r:
        st = r.status
        body = r.read()
    n = len([l for l in base64.b64decode(body).decode().strip().splitlines() if l.strip()])
    print('raw 验证 %s, %d 条' % (st, n))
except Exception as e:
    print('raw 验证失败', repr(e)[:100])
