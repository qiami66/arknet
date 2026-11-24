#!/usr/bin/env bash
# arknet 订阅服务一键安装（systemd）
#   bash install.sh                默认 /opt/arknet，端口 8080，每 6 小时刷新
#   PORT=9000 INTERVAL=3 bash install.sh
#   bash install.sh --no-systemd   只装文件，自己 nohup 跑
set -euo pipefail

PREFIX="${PREFIX:-/opt/arknet}"
PORT="${PORT:-8080}"
INTERVAL="${INTERVAL:-6}"
SERVICE=arknet
SRC="$(cd "$(dirname "$0")" && pwd)"
NO_SYSTEMD=0
[ "${1:-}" = "--no-systemd" ] && NO_SYSTEMD=1

say() { printf '\033[36m[*]\033[0m %s\n' "$*"; }
die() { printf '\033[31m[!]\033[0m %s\n' "$*" >&2; exit 1; }

command -v python3 >/dev/null 2>&1 || die "没装 python3"
PY="$(command -v python3)"
"$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 7) else 1)' \
  || die "python3 版本低于 3.7"

say "python3 = $PY"
say "安装目录 $PREFIX, 端口 $PORT, 刷新间隔 ${INTERVAL}h"

mkdir -p "$PREFIX"
cp -f "$SRC"/*.py "$SRC"/*.json "$PREFIX"/ 2>/dev/null || true
mkdir -p "$PREFIX/assets"
cp -f "$SRC"/assets/*.pem "$PREFIX/assets/" 2>/dev/null || true

# 装之前先自检，链路不通的话装完也是白搭
say "环境自检"
( cd "$PREFIX" && "$PY" doctor.py ) || say "自检有项目没过，装完再看日志排查"

# 首次装的时候跑一次刷新，把凭据换成新鲜的
if [ ! -f "$PREFIX/status.json" ]; then
  say "首次刷新线路（约 30 秒）"
  ( cd "$PREFIX" && "$PY" refresh_all.py ) || say "首次刷新失败，服务起来后会重试"
fi

if [ "$NO_SYSTEMD" = "1" ]; then
  say "不装 systemd，手工启动："
  echo "    cd $PREFIX && nohup $PY run_all.py --port $PORT --interval $INTERVAL > arknet.log 2>&1 &"
  exit 0
fi

[ "$(id -u)" = "0" ] || die "装 systemd 服务要 root，加 sudo 重跑"

cat > /etc/systemd/system/${SERVICE}.service <<EOF
[Unit]
Description=arknet subscription service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$PREFIX
ExecStart=$PY $PREFIX/run_all.py --port $PORT --interval $INTERVAL
Restart=always
RestartSec=10
StandardOutput=append:/var/log/${SERVICE}.log
StandardError=append:/var/log/${SERVICE}.log
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
EOF

touch /var/log/${SERVICE}.log
systemctl daemon-reload
systemctl enable ${SERVICE} >/dev/null
systemctl restart ${SERVICE}

sleep 3
if systemctl is-active --quiet ${SERVICE}; then
  IP="$(curl -s --max-time 5 https://api.ipify.org 2>/dev/null || hostname -I | awk '{print $1}')"
  say "装好了，服务在跑"
  echo
  echo "    小火箭订阅   http://${IP}:${PORT}/sub"
  echo "    Clash 订阅   http://${IP}:${PORT}/clash"
  echo "    FlClash      http://${IP}:${PORT}/flclash"
  echo
  say "放行端口（按需要选一条）"
  echo "    ufw allow ${PORT}/tcp"
  echo "    firewall-cmd --permanent --add-port=${PORT}/tcp && firewall-cmd --reload"
  echo
  say "常用命令"
  echo "    systemctl status ${SERVICE}"
  echo "    journalctl -u ${SERVICE} -f"
  echo "    tail -f /var/log/${SERVICE}.log"
  echo "    cd $PREFIX && $PY refresh_all.py     # 手动刷一次"
else
  die "服务没起来，看 journalctl -u ${SERVICE} -n 50"
fi
