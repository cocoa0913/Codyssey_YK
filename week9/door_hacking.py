import os
import string
import struct
import threading
import zlib
import zipfile
import multiprocessing
from datetime import datetime


_DIR = os.path.dirname(os.path.abspath(__file__))
ZIP_FILE = os.path.join(_DIR, 'emergency_storage_key.zip')
PASSWORD_FILE = os.path.join(_DIR, 'password.txt')
CHARS = string.digits + string.ascii_lowercase
PASSWORD_LENGTH = 6

# Shared counter injected into workers via Pool initializer
_progress = None


def get_current_time_str():
    time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    return f'[{time_str}]'


def save_password(password):
    try:
        with open(PASSWORD_FILE, 'w') as f:
            f.write(password)
        print(f'{get_current_time_str()} Password saved to {PASSWORD_FILE}')
    except OSError as e:
        print(f'{get_current_time_str()} Error saving password: {e}')


# ── ZIP binary parser ─────────────────────────────────────────────────────────
# Local file header layout (byte offsets from header_offset):
#   +14  crc-32          4 B  ← stored UNENCRYPTED (ZipCrypto weakness #1)
#   +26  filename len    2 B
#   +28  extra len       2 B
#   +30  filename / extra   (variable)
#   then: 12-byte enc header  ← last byte is check_byte (weakness #2)
#   then: encrypted payload

def _parse_zip(zip_path):
    with zipfile.ZipFile(zip_path) as zf:
        first_file = zf.namelist()[0]
        info = zf.getinfo(first_file)

    with open(zip_path, 'rb') as f:
        f.seek(info.header_offset + 26)
        fname_len, extra_len = struct.unpack('<HH', f.read(4))
        f.seek(info.header_offset + 30 + fname_len + extra_len)
        raw = f.read(info.compress_size)

    return {
        'filename':      first_file,
        'enc_header':    raw[:12],
        'enc_payload':   raw[12:],
        'check_byte':    (info.CRC >> 24) & 0xFF,
        'crc32':         info.CRC & 0xFFFFFFFF,
        'compress_type': info.compress_type,
    }


# ── ZipCrypto CRC table ───────────────────────────────────────────────────────

def _build_crc_table():
    table = []
    for i in range(256):
        c = i
        for _ in range(8):
            c = (0xEDB88320 ^ (c >> 1)) if c & 1 else (c >> 1)
        table.append(c)
    return table


_CRC_TABLE = _build_crc_table()


# ── Progress monitoring (runs in main process as a daemon thread) ─────────────

def _monitor(counter, total, start_time, stop_evt):
    while not stop_evt.wait(timeout=2.0):
        done = counter.value
        if done == 0:
            continue
        elapsed = (datetime.now() - start_time).total_seconds()
        speed = done / elapsed if elapsed > 0 else 0
        eta = (total - done) / speed if speed > 0 else 0
        print(
            f'{get_current_time_str()} '
            f'{done:,} / {total:,}  '
            f'({done / total * 100:.2f}%)  |  '
            f'{speed:,.0f}/s  |  '
            f'ETA {eta:.0f}s'
        )


# ── Worker initialiser — injects shared counter into each worker process ──────

def _worker_init(counter):
    global _progress
    _progress = counter


# ── Multiprocessing worker ────────────────────────────────────────────────────
# Hot loop uses ZERO stdlib calls: only integer arithmetic and list indexing.
#
# Fast path (255/256):  key-init(6) + header-decrypt(12) + 1 compare → skip
# Slow path  (~1/256):  decrypt full payload + zlib verify + crc32 check

_REPORT_INTERVAL = 500_000


def _crack_range(args):
    (start_idx, end_idx,
     chars, length,
     enc_header, check_byte,
     enc_payload, crc32_val, compress_type) = args

    t = _CRC_TABLE
    base = len(chars)
    K0, K1, K2 = 305419896, 591751049, 878082192
    local_tally = 0

    for idx in range(start_idx, end_idx):

        # index → password as ASCII int list (no string allocation)
        pwd = [0] * length
        i = idx
        for j in range(length - 1, -1, -1):
            pwd[j] = ord(chars[i % base])
            i //= base

        # ZipCrypto key init
        k0, k1, k2 = K0, K1, K2
        for c in pwd:
            k0 = t[(k0 ^ c) & 0xFF] ^ (k0 >> 8)
            k1 = (k1 + (k0 & 0xFF)) & 0xFFFFFFFF
            k1 = (k1 * 134775813 + 1) & 0xFFFFFFFF
            k2 = t[(k2 ^ (k1 >> 24)) & 0xFF] ^ (k2 >> 8)

        # Decrypt 12-byte header, check last decrypted byte
        db = 0
        for eb in enc_header:
            temp = (k2 | 2) & 0xFFFF
            db = (((temp * (temp ^ 1)) >> 8) & 0xFF) ^ eb
            k0 = t[(k0 ^ db) & 0xFF] ^ (k0 >> 8)
            k1 = (k1 + (k0 & 0xFF)) & 0xFFFFFFFF
            k1 = (k1 * 134775813 + 1) & 0xFFFFFFFF
            k2 = t[(k2 ^ (k1 >> 24)) & 0xFF] ^ (k2 >> 8)

        local_tally += 1
        if local_tally == _REPORT_INTERVAL:
            _progress.value += _REPORT_INTERVAL
            local_tally = 0

        if db != check_byte:
            continue                     # ← 255/256 passwords exit here

        # Candidate: full payload decrypt + CRC32 verify
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
            if zlib.crc32(data) & 0xFFFFFFFF == crc32_val:
                _progress.value += local_tally
                return bytes(pwd).decode()
        except zlib.error:
            pass

    _progress.value += local_tally
    return None


# ── Public API ────────────────────────────────────────────────────────────────

def unlock_zip():
    start_time = datetime.now()
    total = len(CHARS) ** PASSWORD_LENGTH
    num_workers = multiprocessing.cpu_count()

    print(f'{get_current_time_str()} unlock_zip() started')
    print(f'{get_current_time_str()} Combinations: {total:,}  |  Workers: {num_workers}')

    try:
        info = _parse_zip(ZIP_FILE)
    except (FileNotFoundError, zipfile.BadZipFile, OSError) as e:
        print(f'{get_current_time_str()} Error: {e}')
        return None

    print(
        f'{get_current_time_str()} '
        f'File: "{info["filename"]}"  |  '
        f'check_byte: 0x{info["check_byte"]:02X}  |  '
        f'payload: {len(info["enc_payload"])} B'
    )

    chunk = (total + num_workers - 1) // num_workers
    ranges = [
        (
            i * chunk,
            min((i + 1) * chunk, total),
            CHARS, PASSWORD_LENGTH,
            info['enc_header'], info['check_byte'],
            info['enc_payload'], info['crc32'], info['compress_type'],
        )
        for i in range(num_workers)
        if i * chunk < total
    ]

    counter = multiprocessing.Value('q', 0)
    stop_evt = threading.Event()
    monitor = threading.Thread(
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
            for result in pool.imap_unordered(_crack_range, ranges):
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
        save_password(found)
    else:
        print(f'{get_current_time_str()} Not found. Elapsed: {elapsed:.2f}s')
    return found


if __name__ == '__main__':
    start_time = datetime.now()
    print(get_current_time_str(), 'main Start..')

    unlock_zip()

    finish_time = datetime.now()
    elapsed = (finish_time - start_time).total_seconds()
    print(get_current_time_str(), f'main Finish..({elapsed}s Elapsed)')
