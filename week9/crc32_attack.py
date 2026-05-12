"""
CRC-32 Collision Attack on ZipCrypto-encrypted ZIP.

Why this works
--------------
ZipCrypto stores the plaintext CRC-32 in the ZIP central directory — in
plain, unencrypted bytes.  For a tiny (11-byte) file we can enumerate every
plausible 11-byte plaintext and compare its CRC-32 against the known value
without ever touching the encryption.

  zlib.crc32()  →  C function, hardware-accelerated (SSE4.2 on x86)
  ZipCrypto check →  pure Python, 18+ arithmetic iterations

So CRC-32 scanning is ~3–5x faster per attempt.  Multiprocessing adds
another N-core multiplier on top.

Usage
-----
  python crc32_attack.py

If the correct pattern is in the PATTERNS list below, it will find the
password without ZipCrypto.  A ZipCrypto round-trip is run only for the
rare CRC-32 match (~1 in 2 billion) to confirm the real password.
"""

import multiprocessing
import os
import string
import struct
import threading
import zipfile
import zlib
from datetime import datetime


_DIR      = os.path.dirname(os.path.abspath(__file__))
ZIP_FILE  = os.path.join(_DIR, 'emergency_storage_key.zip')
PASS_FILE = os.path.join(_DIR, 'password.txt')
CHARS     = string.digits + string.ascii_lowercase
PWD_LEN   = 6
FILE_SIZE = 11            # user-confirmed plaintext size

# ── Pattern table ─────────────────────────────────────────────────────────────
# Each row: (prefix_bytes, suffix_bytes)
# len(prefix) + PWD_LEN + len(suffix) must equal FILE_SIZE (11).
# Add more rows if you have other guesses about the file format.
#
# zlib.crc32 is incremental:
#   CRC32(prefix + pwd + suffix)
#     = zlib.crc32(suffix,
#         zlib.crc32(pwd,
#           zlib.crc32(prefix)))        ← prefix part precomputed once

_RAW_PATTERNS = [
    # prefix (5B) + password (6B) + no suffix
    (b'key: ',  b''),
    (b'pwd: ',  b''),
    (b'pass:',  b''),
    (b'pswd:',  b''),
    (b'pw:  ',  b''),
    # no prefix + password (6B) + suffix (5B)
    (b'',  b'\r\n\r\n\n'),
    (b'',  b'\n\n\n\n\n'),
    (b'',  b'\r\n\r\n\r'),
    (b'',  b'     '),
    (b'',  b'\r\n\r\n\x00'),
    # prefix (1B) + password (6B) + suffix (4B)
    (b' ',  b'\r\n\r\n'),
    (b'\n', b'\r\n\r\n'),
    # prefix (2B) + password (6B) + suffix (3B)
    (b'p:',  b'\r\n\n'),
    (b'k:',  b'\r\n\n'),
    (b'\r\n', b'\r\n\n'),
    # prefix (4B) + password (6B) + suffix (1B)
    (b'pw: ',  b'\n'),
    (b'pw: ',  b'\r'),
    (b'key:',  b'\n'),
    (b'pwd:',  b'\n'),
    # prefix (3B) + password (6B) + suffix (2B)
    (b'pw:',  b'\r\n'),
    (b'key',  b'\r\n'),
]

# Precompute CRC of each prefix so the worker does only ONE incremental
# zlib call per (password × pattern) instead of two.
#   base_crc[i] = zlib.crc32(prefix_i)          ← computed once here
#   per attempt: zlib.crc32(pwd, base_crc[i])   ← extend with password
#                zlib.crc32(suffix_i, mid)       ← extend with suffix
PATTERNS = [(zlib.crc32(p), s) for p, s in _RAW_PATTERNS]


# ── ZIP binary reader ─────────────────────────────────────────────────────────

def _read_zip(zip_path):
    with zipfile.ZipFile(zip_path) as zf:
        name = zf.namelist()[0]
        info = zf.getinfo(name)
    with open(zip_path, 'rb') as f:
        f.seek(info.header_offset + 26)
        fn_len, ex_len = struct.unpack('<HH', f.read(4))
        f.seek(info.header_offset + 30 + fn_len + ex_len)
        raw = f.read(info.compress_size)
    return {
        'name':           name,
        'crc32':          info.CRC & 0xFFFFFFFF,
        'compress_type':  info.compress_type,
        'enc_header':     raw[:12],
        'enc_payload':    raw[12:],
        'check_byte':     (info.CRC >> 24) & 0xFF,
    }


# ── ZipCrypto (confirmation only — called ~1 per 2B candidates) ───────────────

def _build_crc_table():
    table = []
    for i in range(256):
        c = i
        for _ in range(8):
            c = (0xEDB88320 ^ (c >> 1)) if c & 1 else (c >> 1)
        table.append(c)
    return table


_CRC_TABLE = _build_crc_table()


def _zipcrypto_verify(pwd_bytes, enc_header, check_byte,
                      enc_payload, crc32_val, compress_type):
    t = _CRC_TABLE
    k0, k1, k2 = 305419896, 591751049, 878082192
    for c in pwd_bytes:
        k0 = t[(k0 ^ c) & 0xFF] ^ (k0 >> 8)
        k1 = (k1 + (k0 & 0xFF)) & 0xFFFFFFFF
        k1 = (k1 * 134775813 + 1) & 0xFFFFFFFF
        k2 = t[(k2 ^ (k1 >> 24)) & 0xFF] ^ (k2 >> 8)
    db = 0
    for eb in enc_header:
        temp = (k2 | 2) & 0xFFFF
        db = (((temp * (temp ^ 1)) >> 8) & 0xFF) ^ eb
        k0 = t[(k0 ^ db) & 0xFF] ^ (k0 >> 8)
        k1 = (k1 + (k0 & 0xFF)) & 0xFFFFFFFF
        k1 = (k1 * 134775813 + 1) & 0xFFFFFFFF
        k2 = t[(k2 ^ (k1 >> 24)) & 0xFF] ^ (k2 >> 8)
    if db != check_byte:
        return False
    plain = bytearray(len(enc_payload))
    for j, eb in enumerate(enc_payload):
        temp = (k2 | 2) & 0xFFFF
        db = (((temp * (temp ^ 1)) >> 8) & 0xFF) ^ eb
        plain[j] = db
        k0 = t[(k0 ^ db) & 0xFF] ^ (k0 >> 8)
        k1 = (k1 + (k0 & 0xFF)) & 0xFFFFFFFF
        k1 = (k1 * 134775813 + 1) & 0xFFFFFFFF
        k2 = t[(k2 ^ (k1 >> 24)) & 0xFF] ^ (k2 >> 8)
    try:
        data = (zlib.decompress(bytes(plain), -15)
                if compress_type == 8 else bytes(plain))
        return (zlib.crc32(data) & 0xFFFFFFFF) == crc32_val
    except zlib.error:
        return False


# ── Progress ──────────────────────────────────────────────────────────────────

_progress = None
_REPORT   = 500_000


def _worker_init(counter):
    global _progress
    _progress = counter


def get_current_time_str():
    t = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    return f'[{t}]'


def _monitor(counter, total, start_time, stop_evt):
    while not stop_evt.wait(timeout=2.0):
        done = counter.value
        if done == 0:
            continue
        elapsed = (datetime.now() - start_time).total_seconds()
        speed   = done / elapsed if elapsed > 0 else 0
        eta     = (total - done) / speed if speed > 0 else 0
        print(
            f'{get_current_time_str()} '
            f'{done:,} / {total:,}  ({done / total * 100:.2f}%)  |  '
            f'{speed:,.0f}/s  |  ETA {eta:.0f}s'
        )


# ── Worker ────────────────────────────────────────────────────────────────────

def _crc32_crack_range(args):
    """
    For each password candidate:
      1. Run zlib.crc32 for every pattern — no ZipCrypto in this loop.
      2. On CRC-32 match, confirm with full ZipCrypto decryption.

    Hot-path cost per attempt:
      len(PATTERNS) × 2 zlib.crc32 calls (C, hardware-accelerated)
      vs. door_hacking.py's 18-iter Python ZipCrypto pre-filter.
    """
    (start_idx, end_idx,
     chars, pwd_len,
     target_crc32, patterns,
     enc_header, check_byte, enc_payload, compress_type) = args

    base  = len(chars)
    local = 0

    for idx in range(start_idx, end_idx):

        # index → password bytes (no string allocation)
        pwd = [0] * pwd_len
        i   = idx
        for j in range(pwd_len - 1, -1, -1):
            pwd[j] = ord(chars[i % base])
            i //= base
        pwd_bytes = bytes(pwd)

        # ── CRC-32 pattern scan ───────────────────────────────────────────
        # Two incremental zlib.crc32 calls per pattern:
        #   (1) extend prefix_crc with the password
        #   (2) extend that with the suffix
        # Empty suffix: zlib.crc32(b'', mid) == mid  (no-op, still correct)
        hit = False
        for prefix_crc, suffix in patterns:
            mid  = zlib.crc32(pwd_bytes, prefix_crc) & 0xFFFFFFFF
            full = zlib.crc32(suffix,    mid)         & 0xFFFFFFFF
            if full == target_crc32:
                hit = True
                break

        local += 1
        if local == _REPORT:
            _progress.value += _REPORT
            local = 0

        if not hit:
            continue

        # ── CRC-32 matched — full ZipCrypto confirmation ──────────────────
        if _zipcrypto_verify(pwd_bytes, enc_header, check_byte,
                             enc_payload, target_crc32, compress_type):
            _progress.value += local
            return pwd_bytes.decode()

    _progress.value += local
    return None


# ── Public API ────────────────────────────────────────────────────────────────

def crc32_attack():
    start_time = datetime.now()
    total       = len(CHARS) ** PWD_LEN
    num_workers = multiprocessing.cpu_count()

    print(f'{get_current_time_str()} crc32_attack() started')
    print(f'{get_current_time_str()} Patterns: {len(PATTERNS)}  |  '
          f'Combinations: {total:,}  |  Workers: {num_workers}')

    try:
        zi = _read_zip(ZIP_FILE)
    except (FileNotFoundError, zipfile.BadZipFile, OSError) as e:
        print(f'{get_current_time_str()} Error: {e}')
        return None

    print(
        f'{get_current_time_str()} '
        f'File: "{zi["name"]}"  |  '
        f'CRC32: 0x{zi["crc32"]:08X}  |  '
        f'check_byte: 0x{zi["check_byte"]:02X}  |  '
        f'compress: {zi["compress_type"]}'
    )

    chunk  = (total + num_workers - 1) // num_workers
    ranges = [
        (
            i * chunk, min((i + 1) * chunk, total),
            CHARS, PWD_LEN,
            zi['crc32'], PATTERNS,
            zi['enc_header'], zi['check_byte'],
            zi['enc_payload'], zi['compress_type'],
        )
        for i in range(num_workers)
        if i * chunk < total
    ]

    counter  = multiprocessing.Value('q', 0)
    stop_evt = threading.Event()
    monitor  = threading.Thread(
        target=_monitor,
        args=(counter, total, start_time, stop_evt),
        daemon=True,
    )
    monitor.start()

    found = None
    try:
        with multiprocessing.Pool(
            processes=num_workers,
            initializer=_worker_init,
            initargs=(counter,),
        ) as pool:
            for result in pool.imap_unordered(_crc32_crack_range, ranges):
                if result is not None:
                    found = result
                    pool.terminate()
                    break
    except (FileNotFoundError, zipfile.BadZipFile, OSError) as e:
        print(f'{get_current_time_str()} Error: {e}')
    finally:
        stop_evt.set()
        monitor.join()

    elapsed = (datetime.now() - start_time).total_seconds()
    if found:
        print(f'{get_current_time_str()} SUCCESS! Password: {found}')
        print(f'{get_current_time_str()} Elapsed: {elapsed:.2f}s')
        try:
            with open(PASS_FILE, 'w') as f:
                f.write(found)
            print(f'{get_current_time_str()} Saved to {PASS_FILE}')
        except OSError as e:
            print(f'{get_current_time_str()} Error saving: {e}')
    else:
        print(f'{get_current_time_str()} Not found with current patterns. ({elapsed:.2f}s)')
        print(f'{get_current_time_str()} Hint: add the actual file format to _RAW_PATTERNS '
              f'and re-run, or fall back to door_hacking.py')
    return found


if __name__ == '__main__':
    start_time = datetime.now()
    print(get_current_time_str(), 'main Start..')

    crc32_attack()

    finish_time = datetime.now()
    elapsed = (finish_time - start_time).total_seconds()
    print(get_current_time_str(), f'main Finish..({elapsed}s Elapsed)')
