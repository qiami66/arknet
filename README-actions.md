# 让 GitHub 帮你自动刷新（电脑关机也不影响）

## 为什么不能在云服务器上刷

那台机器是纯国内网络，实测：

```
ping 142.248.139.105   100% 丢包
8.8.8.8:53              No route to host
api.github.com          No route to host
curl zz44:14215         No route to host (errno 113)
```

国内路由只放行国内段，所有境外 IP 全是 `EHOSTUNREACH`。所以它连不上接口，签不出凭据，只能当订阅托管。

刷新得放在**能连境外的机器**上。GitHub Actions 的 runner 就是免费的境外机器，每 6 小时帮你跑一次，你自己的电脑关不关机都无所谓。

## 准备

1. 一个 GitHub 账号（没有就注册一个，免费）
2. 本目录的 `arknet-actions.zip`（已经打好）

## 四步装好

### 第 1 步：建仓库

打开 https://github.com/new

- Repository name 随便写，比如 `arknet`
- 选 **Private**（一定要私有，里面有账号密码）
- 点 **Create repository**

### 第 2 步：上传文件

解压 `arknet-actions.zip`，把里面的文件全部拖进刚建好的仓库页面（点「uploading an existing file」的链接，或者直接把文件拖到文件列表区域）。

拖完点底下绿色的 **Commit changes**。

`.github` 这个隐藏目录拖不进去，所以要单独建，见第 3 步。

### 第 3 步：建 workflow 文件

在仓库首页点 **Add file → Create new file**。

文件名那里**照抄**这一整行（斜杠会自动变成目录）：

```
.github/workflows/refresh.yml
```

下面的大框里粘贴：

```yaml
name: arknet refresh

on:
  schedule:
    - cron: '0 */6 * * *'
  workflow_dispatch:

jobs:
  refresh:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: install
        run: pip install --quiet paramiko
      - name: refresh
        run: python refresh_all.py
      - name: push
        env:
          CLOUD_PASSWORD: ${{ secrets.CLOUD_PASSWORD }}
        run: python sync.py --no-refresh
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: nodes
          path: |
            nodes_full.json
            shadowrocket_anytls_live.txt
```

点右上 **Commit changes**。

### 第 4 步：加密码

仓库页 → **Settings** → 左侧 **Secrets and variables** → **Actions** → 绿色按钮 **New repository secret**

- Name：`CLOUD_PASSWORD`
- Secret：`N8iL02sPdwJz`

点 **Add secret**。

## 跑第一次

仓库页 → **Actions** 标签 → 左边选 **arknet refresh** → 右边 **Run workflow** → 绿色按钮。

等 1-2 分钟，看到绿色对勾就是成功。点进去能看到刷新日志，16 条全 `ALIVE`。

之后每 6 小时自动跑，你要做的只有一件事：**手机上的订阅到点自己拉就行**。

## 验证方式

手机上拉一次订阅，或者浏览器打开：

```
http://103.236.88.52:50256/health
```

返回的 `nodes` 是 16 就正常。

## 注意

- 仓库必须 **Private**，因为 `accounts.json` 里有那 6 个账号的密码
- `cloud.local.json`（本地密码文件）不要上传，`.gitignore` 已经挡住了
- GitHub Actions 免费额度每月 2000 分钟，这套一次跑 1 分钟左右，6 小时一次，一个月约 60 分钟，用不完
- 想改成 3 小时一次，把 `cron: '0 */6 * * *'` 改成 `cron: '0 */3 * * *'`
