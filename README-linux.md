# arknet 订阅服务（Linux / Ubuntu 22.04）

把狐狸 APK 的 16 条美国 AnyTLS 线路搬到 Linux 服务器上，定时自动重签，对外提供订阅地址。

## 一键装

```bash
tar -xzf arknet-linux.tar.gz
cd arknet-linux
sudo bash install.sh
```

`install.sh` 会先跑 `doctor.py` 自检，链路不通会当场提示，不会闷头装完再让你猜。

装完会打印：

```
小火箭订阅   http://<服务器公网IP>:8080/sub
Clash 订阅   http://<服务器公网IP>:8080/clash
FlClash      http://<服务器公网IP>:8080/flclash
```

自定义端口和刷新间隔：

```bash
sudo PORT=9000 INTERVAL=3 bash install.sh
```

只要文件不要 systemd：

```bash
bash install.sh --no-systemd
cd /opt/arknet && nohup python3 run_all.py --port 8080 --interval 6 > arknet.log 2>&1 &
```

Ubuntu 22.04 自带 python3.10，不用装任何依赖，纯标准库。

## 订阅地址

| 路由 | 内容 |
|---|---|
| `/sub` | Shadowrocket 订阅（base64 节点列表） |
| `/plain` | 明文 `anytls://` 列表 |
| `/clash` | Clash / mihomo 完整配置 |
| `/flclash` | FlClash 完整配置 |
| `/health` | `{"nodes":16,"port":8080}` |

全部带 `Subscription-Userinfo` 和 `Profile-Update-Interval: 12`，客户端能识别。

## 它怎么跑

`run_all.py` 一个进程干三件事：

1. 启动时立刻重签 16 条线路（6 个账号 × 3 设备槽）
2. 起 HTTP 订阅服务（默认 8080）
3. 每 `--interval` 小时重签一次，失败重试 3 次，不退出

订阅服务每次请求现读 `nodes_full.json`，所以刷新完客户端下次拉就是新的，不用重启任何东西。

**关键点**：凭据是服务端现签的，节点会定期清空用户表。实测隔一夜 16 条全废，重签立即恢复。所以自动刷新的间隔别设太短（会浪费登录），也别太长（过期太久），6 小时合适。

## 装之前先自检：doctor.py

```bash
python3 doctor.py
```

五项检查，几秒出结果：

```
[ OK ] python 版本                  3.10.12
[ OK ] API 可达                     HTTP 400（没签名的正常拒绝，说明服务在）
[ OK ] 系统时钟偏差                     1 秒
[ OK ] 节点端口 noded1.gykisjdcth.top 10021 可达 205ms
[ OK ] 节点链路                       3/3 个样本可达
[ OK ] 现有凭据在线                     16/16
```

这台机器能不能跑，看完这一屏就知道。哪项红了照着排：

| 红的是 | 说明 |
|---|---|
| API 可达 | 这台机器连不上 `zz11.qjfifnbotx.top:14215`，换台机器或者检查出网 |
| 系统时钟偏差 | 时钟不准，接口签名会被拒，`ntpdate` 校时 |
| 节点链路 | 连不上 `nodedN.*:10021`，这台机器的出口被墙了，换节点/换机房 |
| 现有凭据在线 | 凭据过期，跑一次 `refresh_all.py` |

## 手动操作

```bash
cd /opt/arknet

python3 refresh_all.py             # 重签全部
python3 refresh_all.py --account uplie5c68bp   # 只重签一个账号名下的 3 条
python3 refresh_all.py --check      # 不重签，只验活并重写文件
python3 refresh_all.py --list       # 看槽位分配

python3 sub_server.py 9000          # 只起订阅服务
systemctl restart arknet            # 重启守护进程
journalctl -u arknet -f             # 看日志
tail -f /var/log/arknet.log         # 同上，文件版
```

## 文件

| 文件 | 作用 |
|---|---|
| `client.py` | 复刻 `X-Content-Security` 签名 + 响应 AES 解密 |
| `crypto_ecb.py` | 纯 Python AES-256 / RSA PKCS#1 v1.5 |
| `anytls_probe.py` | AnyTLS 认证探针（验活就是靠它） |
| `refresh_all.py` | 重签 + 生成全部格式文件 |
| `sub_server.py` | 订阅 HTTP 服务 |
| `run_all.py` | 定时刷新 + 订阅服务，systemd 跑这个 |
| `accounts.json` | 6 个账号 |
| `nodes_full.json` | 16 条节点的当前凭据（唯一数据源） |
| `assets/*.pem` | 接口签名用的 RSA 公钥 |

所有配置文件都由 `nodes_full.json` 生成，端口、密码变了只需要重签，不用手改 YAML。

## 账号槽位

| 账号 | 承担节点 |
|---|---|
| uplie5c68bp@gmail.com | D2 / G2 / H2 |
| u5gvtk9g50h@gmail.com | D3 / G3 / H3 |
| uje545yx4ip@gmail.com | D4 / G4 / H4 |
| uo60tny1bg@gmail.com | D5 / G5 / H5 |
| uzdc1lm0n6@gmail.com | F1 / G1 / H1 |
| ub0ohtkt8i@gmail.com | D1 |

密码统一 `Aa123456!`。每个账号 3 个设备槽，一条线路占一个。要加线路就加账号（注册限 3 号/IP，需要换出口 IP 注册）。

## 防火墙

```bash
sudo ufw allow 8080/tcp
# 或
sudo firewall-cmd --permanent --add-port=8080/tcp && sudo firewall-cmd --reload
```

云厂商的安全组也要放行同一个端口。

## 排障

**订阅能拉到但节点全红**
凭据过期了。跑 `python3 refresh_all.py` 看输出，`ALIVE` 才算好。输出 `LOGIN FAIL` 说明账号被限流或者密码变了。

**`/sub` 返回空**
`nodes_full.json` 里没有 `alive=true` 的节点。跑一次刷新。

**端口连不上**
`ss -lntp | grep 8080` 看有没有监听；再看防火墙和云安全组。

**系统时间不准**
接口签名带时间戳，服务器时钟偏差大于几分钟会被拒。`timedatectl` 查一下，`sudo ntpdate ntp.aliyun.com` 校时。
