"""本地刷新 + 推送到云服务器。

  python sync.py                刷新全部账号 -> 推 nodes_full.json 上去
  python sync.py --no-refresh   只推送（不重签）
  python sync.py --check        只验证本地凭据

配置来源优先级：环境变量 > cloud.local.json > cloud.json
  CLOUD_HOST / CLOUD_PORT / CLOUD_USER / CLOUD_PASSWORD / CLOUD_REMOTE
"""
import json, sys, os, pathlib, hashlib

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import refresh_all as R


def load_cfg():
    cfg = json.loads((HERE / 'cloud.json').read_text(encoding='utf-8'))
    local = HERE / 'cloud.local.json'
    if local.exists():
        cfg.update(json.loads(local.read_text(encoding='utf-8')))
    for key, env in [('host', 'CLOUD_HOST'), ('port', 'CLOUD_PORT'), ('user', 'CLOUD_USER'),
                     ('password', 'CLOUD_PASSWORD'), ('remote', 'CLOUD_REMOTE')]:
        if os.environ.get(env):
            cfg[key] = os.environ[env]
    if not cfg.get('password'):
        raise SystemExit('缺少服务器密码：设环境变量 CLOUD_PASSWORD，或写 cloud.local.json')
    return cfg


def push():
    import paramiko
    cfg = load_cfg()
    local = HERE / 'nodes_full.json'
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(cfg['host'], port=int(cfg['port']), username=cfg['user'],
              password=cfg['password'], timeout=30, auth_timeout=30)
    sftp = c.open_sftp()
    sftp.put(str(local), cfg['remote'])
    sftp.close()
    _, out, _ = c.exec_command('md5sum %s; curl -s http://127.0.0.1:8080/health' % cfg['remote'], timeout=30)
    res = out.read().decode('utf-8', 'replace').strip()
    c.close()
    print('本地 md5 %s' % hashlib.md5(local.read_bytes()).hexdigest())
    print('远端 %s' % res.replace('\n', '  '))


if __name__ == '__main__':
    arg = sys.argv[1] if len(sys.argv) > 1 else ''
    if arg == '--check':
        R.cmd_check()
    else:
        if arg != '--no-refresh':
            R.cmd_refresh()
        push()
