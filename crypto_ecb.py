"""Pure-python AES-256 ECB + RSA PKCS#1 v1.5 to reproduce arknet X-Content-Security."""
import os, struct

# ---------- AES-256 (ECB) ----------
SBOX = [
0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16]
RCON = [0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80,0x1b,0x36,0x6c,0xd8,0xab,0x4d]

def _xtime(a):
    a <<= 1
    if a & 0x100:
        a = (a ^ 0x11b) & 0xff
    return a

def _mul(a, b):
    r = 0
    for _ in range(8):
        if b & 1:
            r ^= a
        b >>= 1
        a = _xtime(a)
    return r

def _expand(key):
    nk = len(key) // 4
    nr = nk + 6
    w = [list(key[4*i:4*i+4]) for i in range(nk)]
    for i in range(nk, 4*(nr+1)):
        t = list(w[i-1])
        if i % nk == 0:
            t = t[1:] + t[:1]
            t = [SBOX[b] for b in t]
            t[0] ^= RCON[i//nk - 1]
        elif nk > 6 and i % nk == 4:
            t = [SBOX[b] for b in t]
        w.append([w[i-nk][j] ^ t[j] for j in range(4)])
    return [sum(w[4*r:4*r+4], []) for r in range(nr+1)], nr

def _add_round_key(s, k):
    return [s[i] ^ k[i] for i in range(16)]

def _shift_rows(s):
    o = list(s)
    for r in range(1, 4):
        row = [s[r + 4*c] for c in range(4)]
        row = row[r:] + row[:r]
        for c in range(4):
            o[r + 4*c] = row[c]
    return o

def _inv_shift_rows(s):
    o = list(s)
    for r in range(1, 4):
        row = [s[r + 4*c] for c in range(4)]
        row = row[-r:] + row[:-r]
        for c in range(4):
            o[r + 4*c] = row[c]
    return o

def _mix_columns(s):
    o = [0]*16
    for c in range(4):
        a = s[4*c:4*c+4]
        o[4*c+0] = _mul(a[0],2) ^ _mul(a[1],3) ^ a[2] ^ a[3]
        o[4*c+1] = a[0] ^ _mul(a[1],2) ^ _mul(a[2],3) ^ a[3]
        o[4*c+2] = a[0] ^ a[1] ^ _mul(a[2],2) ^ _mul(a[3],3)
        o[4*c+3] = _mul(a[0],3) ^ a[1] ^ a[2] ^ _mul(a[3],2)
    return o

INV_SBOX = [0]*256
for _i, _v in enumerate(SBOX):
    INV_SBOX[_v] = _i

def _inv_mix_columns(s):
    o = [0]*16
    for c in range(4):
        a = s[4*c:4*c+4]
        o[4*c+0] = _mul(a[0],14) ^ _mul(a[1],11) ^ _mul(a[2],13) ^ _mul(a[3],9)
        o[4*c+1] = _mul(a[0],9) ^ _mul(a[1],14) ^ _mul(a[2],11) ^ _mul(a[3],13)
        o[4*c+2] = _mul(a[0],13) ^ _mul(a[1],9) ^ _mul(a[2],14) ^ _mul(a[3],11)
        o[4*c+3] = _mul(a[0],11) ^ _mul(a[1],13) ^ _mul(a[2],9) ^ _mul(a[3],14)
    return o

class AES:
    def __init__(self, key):
        self.rk, self.nr = _expand(key)

    def encrypt_block(self, b):
        s = _add_round_key(list(b), self.rk[0])
        for r in range(1, self.nr):
            s = [SBOX[x] for x in s]
            s = _shift_rows(s)
            s = _mix_columns(s)
            s = _add_round_key(s, self.rk[r])
        s = [SBOX[x] for x in s]
        s = _shift_rows(s)
        return bytes(_add_round_key(s, self.rk[self.nr]))

    def decrypt_block(self, b):
        s = _add_round_key(list(b), self.rk[self.nr])
        for r in range(self.nr-1, 0, -1):
            s = _inv_shift_rows(s)
            s = [INV_SBOX[x] for x in s]
            s = _add_round_key(s, self.rk[r])
            s = _inv_mix_columns(s)
        s = _inv_shift_rows(s)
        s = [INV_SBOX[x] for x in s]
        return bytes(_add_round_key(s, self.rk[0]))

def pkcs7(b, bs=16):
    n = bs - len(b) % bs
    return b + bytes([n])*n

def unpkcs7(b, bs=16):
    if not b:
        return b
    n = b[-1]
    if 1 <= n <= bs:
        return b[:-n]
    return b

def aes_ecb_encrypt(key, data):
    c = AES(key)
    data = pkcs7(data)
    return b''.join(c.encrypt_block(data[i:i+16]) for i in range(0, len(data), 16))

def aes_ecb_decrypt(key, data):
    c = AES(key)
    out = b''.join(c.decrypt_block(data[i:i+16]) for i in range(0, len(data), 16))
    return unpkcs7(out)

# ---------- RSA PKCS#1 v1.5 ----------
def parse_spki(pem_path):
    import base64
    txt = open(pem_path, 'r', encoding='utf-8').read()
    b64 = ''.join(l for l in txt.splitlines() if '-----' not in l)
    der = base64.b64decode(b64)
    # minimal DER walk: SEQUENCE { SEQUENCE{alg}, BITSTRING{ SEQUENCE{ INTEGER n, INTEGER e } } }
    def read_tlv(buf, off):
        tag = buf[off]
        ln = buf[off+1]
        off += 2
        if ln & 0x80:
            n = ln & 0x7f
            ln = int.from_bytes(buf[off:off+n], 'big')
            off += n
        return tag, buf[off:off+ln], off+ln

    tag, seq, _ = read_tlv(der, 0)
    _, alg, off = read_tlv(seq, 0)
    tag, bits, _ = read_tlv(seq, off)
    inner = bits[1:]  # skip unused-bits byte
    _, rsaseq, _ = read_tlv(inner, 0)
    _, n_bytes, off = read_tlv(rsaseq, 0)
    _, e_bytes, _ = read_tlv(rsaseq, off)
    return int.from_bytes(n_bytes, 'big'), int.from_bytes(e_bytes, 'big')

def rsa_pkcs1_encrypt(pubkey_path, msg):
    n, e = parse_spki(pubkey_path)
    k = (n.bit_length() + 7) // 8
    if len(msg) > k - 11:
        raise ValueError('message too long')
    ps = b''
    while len(ps) < k - len(msg) - 3:
        b = os.urandom(1)
        if b != b'\x00':
            ps += b
    em = b'\x00\x02' + ps + b'\x00' + msg
    m = int.from_bytes(em, 'big')
    c = pow(m, e, n)
    return c.to_bytes(k, 'big')
