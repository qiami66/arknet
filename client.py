"""arknet 客户端：复刻 X-Content-Security 请求签名 + 响应解密。跨平台，仅标准库。"""
import ssl, json, os, time, hashlib, hmac, base64, urllib.request, urllib.error
import pathlib

import crypto_ecb as C

HERE = pathlib.Path(__file__).resolve().parent
PUB = str(HERE / 'assets' / 'client-bff-rsa-prod2.public.pem')
EMPTY_SHA = 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
APP_KEY = 'client-rsa-prod2-v1'
CHANNEL = '66bdce80'

_ctx = ssl.create_default_context()
_ctx.check_hostname = False
_ctx.verify_mode = ssl.CERT_NONE

B64 = lambda b: base64.b64encode(b).decode()

def b64d(s):
    s = ''.join(s.split())
    return base64.b64decode(s + '=' * ((-len(s)) % 4))

def base_headers():
    return {
        'channel-code': CHANNEL,
        'device-id': 'a1b2c3d4e5f60718293a4b5c6d7e8f90',
        'platform': 'android',
        'model': 'Pixel 7',
        'locale': 'zh-CN',
        'distribution-channel': 'free',
        'user-agent': 'ArkNetAndroid',
        'timezone': 'Asia/Shanghai',
        'accept': 'application/json',
    }

def call(base, path, method='GET', body=None, token=None, device_id=None):
    """发一个签名请求。base 例: https://zz11.qjfifnbotx.top:14215"""
    query = ''
    if '?' in path:
        path, query = path.split('?', 1)
    body_bytes = json.dumps(body, separators=(',', ':')).encode() if body is not None else None

    key = os.urandom(32)
    enc_body = B64(C.aes_ecb_encrypt(key, body_bytes)).encode() if body_bytes else None
    ts = str(int(time.time()))
    digest = hashlib.sha256(enc_body).hexdigest() if enc_body else EMPTY_SHA
    sts = '\n'.join([ts, method.upper(), '/' + path.lstrip('/'), query, digest])
    sig = B64(hmac.new(key, sts.encode(), hashlib.sha256).digest())
    inner = 'version=v1; type=1; key=%s; time=%s' % (B64(key), ts)
    secret = B64(C.rsa_pkcs1_encrypt(PUB, inner.encode()))

    h = base_headers()
    if device_id:
        h['device-id'] = device_id
    if token:
        h['authorization'] = token
    h['X-Content-Security'] = 'key=%s; secret=%s; signature=%s' % (APP_KEY, secret, sig)
    if enc_body is not None:
        h['content-type'] = 'application/json; charset=utf-8'

    url = base.rstrip('/') + path + (('?' + query) if query else '')
    r = urllib.request.Request(url, data=enc_body, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, context=_ctx, timeout=30) as resp:
            st, raw = resp.status, resp.read()
    except urllib.error.HTTPError as e:
        st, raw = e.code, e.read()
    except Exception as e:
        return None, repr(e)

    txt = raw.decode('utf-8', 'replace').strip()
    if txt.startswith('{') or txt.startswith('['):
        return st, txt
    try:
        ct = b64d(txt)
        if ct and len(ct) % 16 == 0:
            return st, C.aes_ecb_decrypt(key, ct).decode('utf-8', 'replace')
    except Exception as e:
        return st, 'DECRYPT_FAIL %s: %s' % (e, txt[:200])
    return st, txt
