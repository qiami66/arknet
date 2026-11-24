"""常驻进程：定时重签线路 + 对外提供订阅，一个进程全包。

  python3 run_all.py                         # 8080 端口，每 6 小时刷新
  python3 run_all.py --port 9000 --interval 3
  python3 run_all.py --no-start-refresh      # 起来先不刷，用现有凭据

systemd 下由 install.sh 托管；手工跑就 nohup python3 run_all.py & 即可。
"""
import argparse, json, signal, sys, threading, time, datetime, pathlib, traceback

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import refresh_all as R
import sub_server as S

STOP = threading.Event()


def log(msg):
    ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print('[%s] %s' % (ts, msg), flush=True)


def do_refresh():
    log('开始刷新线路')
    try:
        R.cmd_refresh()
    except Exception:
        log('刷新异常：\n%s' % traceback.format_exc())
        return False
    try:
        db = json.loads((HERE / 'nodes_full.json').read_text(encoding='utf-8'))
        live = sum(1 for n in db['nodes'] if n.get('alive'))
        status = {
            'last_refresh': int(time.time()),
            'last_refresh_text': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'live': live,
            'total': len(db['nodes']),
        }
        (HERE / 'status.json').write_text(json.dumps(status, ensure_ascii=False, indent=1), encoding='utf-8')
        log('刷新完成，在线 %d/%d' % (live, len(db['nodes'])))
        return True
    except Exception:
        log('写状态失败：\n%s' % traceback.format_exc())
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=8080)
    ap.add_argument('--interval', type=float, default=6.0, help='刷新间隔，单位小时')
    ap.add_argument('--no-start-refresh', action='store_true')
    a = ap.parse_args()

    if not a.no_start_refresh:
        do_refresh()

    threading.Thread(target=S.serve, kwargs={'host': '0.0.0.0', 'port': a.port}, daemon=True).start()
    log('订阅服务已启动，端口 %d' % a.port)

    def stop(signum, frame):
        STOP.set()
        log('收到信号 %s，准备退出' % signum)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    next_run = time.time() + max(0.1, a.interval) * 3600
    log('下次刷新：%s' % datetime.datetime.fromtimestamp(next_run).strftime('%Y-%m-%d %H:%M:%S'))
    while not STOP.wait(30):
        if time.time() >= next_run:
            do_refresh()
            next_run = time.time() + max(0.1, a.interval) * 3600
            log('下次刷新：%s' % datetime.datetime.fromtimestamp(next_run).strftime('%Y-%m-%d %H:%M:%S'))
    log('已退出')


if __name__ == '__main__':
    main()
