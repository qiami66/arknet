"""常驻守护：每 N 小时刷新线路并推送到云服务器。

  python daemon.py            默认 6 小时一轮
  python daemon.py 3          3 小时一轮
  python daemon.py --once     只跑一轮就退出
"""
import subprocess, sys, time, datetime, pathlib

HERE = pathlib.Path(__file__).resolve().parent
LOG = HERE / 'sync.log'
INTERVAL_H = 6.0
args = [a for a in sys.argv[1:] if not a.startswith('--')]
if args:
    try:
        INTERVAL_H = float(args[0])
    except ValueError:
        pass
ONCE = '--once' in sys.argv


def log(msg):
    line = '[%s] %s' % (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), msg)
    print(line, flush=True)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


def run_once():
    log('开始刷新并推送')
    try:
        p = subprocess.run([sys.executable, str(HERE / 'sync.py')], cwd=str(HERE),
                           capture_output=True, text=True, encoding='utf-8', errors='replace')
        for line in (p.stdout or '').strip().splitlines():
            log('  ' + line)
        if p.returncode != 0:
            for line in (p.stderr or '').strip().splitlines()[:8]:
                log('  [err] ' + line)
            log('本轮失败，退出码 %s' % p.returncode)
            return False
        log('本轮完成')
        return True
    except Exception as e:
        log('异常: %r' % e)
        return False


if __name__ == '__main__':
    log('守护启动，间隔 %.1f 小时' % INTERVAL_H)
    while True:
        run_once()
        if ONCE:
            break
        nxt = datetime.datetime.now() + datetime.timedelta(hours=INTERVAL_H)
        log('下次 %s' % nxt.strftime('%Y-%m-%d %H:%M:%S'))
        time.sleep(INTERVAL_H * 3600)
