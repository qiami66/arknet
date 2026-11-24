"""Minimal AnyTLS auth probe: does <password> authenticate on <host:port> with <sni>?"""
import json, socket, ssl, struct, hashlib, sys, time

DEFAULT_SCHEME = (
    "stop=8\n"
    "0=30-30\n"
    "1=100-400\n"
    "2=400-500,c,500-1000,c,500-1000,c,500-1000,c,500-1000\n"
    "3=9-9,500-1000\n"
    "4=500-1000\n"
    "5=500-1000\n"
    "6=500-1000\n"
    "7=500-1000"
)

def frame(cmd, sid, data=b''):
    return struct.pack('!BIH', cmd, sid, len(data)) + data

def probe(host, port, sni, password, timeout=10):
    ctx = ssl.create_default_context()
    s = socket.create_connection((host, port), timeout=timeout)
    ss = ctx.wrap_socket(s, server_hostname=sni)
    ss.settimeout(timeout)
    pw = hashlib.sha256(password.encode()).digest()
    pad = bytes(30)
    ss.sendall(pw + struct.pack('!H', len(pad)) + pad)
    settings = f"v=2\nclient=anytls-probe/0.0.1\npadding-md5={hashlib.md5(DEFAULT_SCHEME.encode()).hexdigest()}".encode()
    ss.sendall(frame(4, 0, settings))
    ss.sendall(frame(1, 1))
    ss.sendall(frame(2, 1, b'\x01\x01\x01\x01\x01\xbb'))
    got = b''
    try:
        got = ss.recv(4096)
    except Exception as e:
        return False, f'recv-error {e}'
    finally:
        try:
            ss.close()
        except Exception:
            pass
    if not got:
        return False, 'closed-without-data'
    cmds = []
    i = 0
    while i + 7 <= len(got):
        c, sid, ln = struct.unpack('!BIH', got[i:i+7])
        cmds.append((c, sid, ln, got[i+7:i+7+ln][:40]))
        i += 7 + ln
    return True, cmds

if __name__ == '__main__':
    recs = json.load(open('connects.json', encoding='utf-8'))
    okn = 0
    for r in recs:
        c = r['connect']
        name = r['meta']['name']
        try:
            ok, info = probe(c['ingress'], c['listenPort'], c['tlsServerName'] or c['ingress'], c['password'])
        except Exception as e:
            ok, info = False, repr(e)
        if ok:
            okn += 1
        print(f'{name:8s} {"AUTH-OK " if ok else "AUTH-FAIL"} {info}')
    print(f'auth ok: {okn}/{len(recs)}')
