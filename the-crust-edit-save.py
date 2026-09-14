#!/usr/bin/env python3
"""Offline save editor for The Crust (UE 4.27, single-player).

Currently edits the credits balance of a save slot. The balance is read
from the tail of the PlayerCredits/GeneralCredits series in Stats.bin, then
patched in Level.sav at FloatProperty-tagged occurrences only.

Level.sav is a concatenation of [48-byte header + zlib stream] chunks. The
header holds magic c1832a9e and duplicated u64 compressed/decompressed
sizes. The format carries no checksum, so equal-length float replacement
is safe. Stats.bin is never modified.

Close the game before patching and keep Steam Cloud off for it, otherwise
the cloud can re-upload the old save.

Usage:
    the-crust-edit-save.py <slot-dir> --detect       print current balance
    the-crust-edit-save.py <slot-dir> [new_value]    patch (backup -> Level.sav.bak)
new_value defaults to 1000000; float32 is exact up to 16777216.
"""
import pathlib, struct, sys, zlib

MAGIC = bytes.fromhex('c1832a9e')
HDR = 48

def read_chunks(fn: pathlib.Path):
    b = fn.read_bytes()
    assert b[:4] == MAGIC, 'bad magic'
    out = []  # (header, compressed, decompressed)
    i = 0
    while i < len(b):
        assert b[i:i+4] == MAGIC, f'bad header @{hex(i)}'
        csize, dsize = struct.unpack_from('<QQ', b, i + 0x10)
        comp = b[i+HDR : i+HDR+csize]
        part = zlib.decompress(comp)
        assert len(part) == dsize, 'dsize mismatch'
        out.append((b[i:i+HDR], comp, part))
        i += HDR + csize
    return b, out

def write_chunks(fn: pathlib.Path, chunks):
    out = bytearray()
    for hdr, comp, part in chunks:
        newhdr = bytearray(hdr[:HDR])
        struct.pack_into('<QQQQ', newhdr, 16, len(comp), len(part), len(comp), len(part))
        out += bytes(newhdr) + comp
    fn.write_bytes(bytes(out))

def balance_from_stats(slot: pathlib.Path):
    sb = (slot / 'Stats.bin').read_bytes()
    p = 0
    last = {}
    while p < len(sb):
        ln, = struct.unpack_from('<i', sb, p); p += 4
        if p + ln*2 + 4 > len(sb): break
        name = sb[p:p+ln*2].decode('utf-16-le'); p += ln*2
        cnt, = struct.unpack_from('<i', sb, p); p += 4
        vals = [struct.unpack_from('<f', sb, p + i*12)[0] for i in range(cnt)]
        p += cnt*12
        last[name] = vals[-1] if vals else None
    for k in ('PlayerCredits', 'GeneralCredits'):
        if last.get(k) is not None:
            return last[k]
    return None

def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    slot = pathlib.Path(sys.argv[1])
    ln = slot / 'Level.sav'
    assert ln.exists(), f'no {ln}'

    old = balance_from_stats(slot)
    if old is None:
        sys.exit('could not detect balance from Stats.bin')
    print(f'current credits: {old:g}')
    if '--detect' in sys.argv:
        return
    args = [a for a in sys.argv[2:] if not a.startswith('-')]
    new = float(args[0]) if args else 1_000_000.0
    print(f'target credits : {new:g}')

    raw, chunks = read_chunks(ln)
    oldb, newb = struct.pack('<f', old), struct.pack('<f', new)

    def float_property_value(part, i):
        # value of a FloatProperty: "FloatProperty" tag within 32 bytes before value
        w = part[max(0, i-32):i]
        f = w.rfind(b'FloatProperty')
        n = w.rfind(b'IntProperty')
        return f >= 0 and f > n

    changed = 0
    for ci, (hdr, comp, part) in enumerate(chunks):
        positions = []
        start = 0
        while True:
            m = part.find(oldb, start)
            if m < 0: break
            if float_property_value(part, m):
                positions.append(m)
            start = m + 1
        if not positions:
            continue
        part = bytearray(part)
        for pos in positions:
            part[pos:pos+4] = newb
        chunk = bytes(part)
        chunks[ci] = (hdr, zlib.compress(chunk, 9), chunk)
        changed += len(positions)
        print(f'  chunk {ci}: patched {len(positions)} float occurrence(s)')

    if not changed:
        sys.exit('no FloatProperty-tagged balance floats found — aborting, nothing written')

    bak = slot / 'Level.sav.bak'
    if not bak.exists():
        bak.write_bytes(raw)
        print(f'backup: {bak}')
    write_chunks(ln, chunks)

    _, chk = read_chunks(ln)
    total = sum(p.count(newb) for _, _, p in chk)
    left = sum(p.count(oldb) for _, _, p in chk)
    print(f'verify: {total} patched floats present, {left} old floats left')

if __name__ == '__main__':
    main()
