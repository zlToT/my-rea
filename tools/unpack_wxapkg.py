#!/usr/bin/env python3
"""Generic unpacker for plain (unencrypted) WeChat wxapkg files.

Supports the two common index variants:
  A) header.info1 = file count, index starts with the first entry
  B) header.info1 = 0, index starts with a uint32 file count

Offsets in the index are absolute file offsets in most packages, but some
tools emit offsets relative to the data section; both are auto-detected.

Usage:
  python unpack_wxapkg.py <file.wxapkg | directory> [outdir]
"""
import os
import struct
import sys

MAGIC = 0xBE
MARK = 0xED
PNG = b"\x89PNG\r\n\x1a\n"


def u32(buf, off):
    return struct.unpack_from(">I", buf, off)[0]


def read_header(data):
    if len(data) < 14 or data[0] != MAGIC:
        raise ValueError("not a plain wxapkg (magic != 0xBE)")
    info1, idx_len, body_len, mark = struct.unpack(">IIIB", data[1:14])
    if mark != MARK:
        print(f"  warning: lastMark=0x{mark:02X}, expected 0xED")
    if 14 + idx_len + body_len != len(data):
        print(f"  warning: header size mismatch: 14+{idx_len}+{body_len} != {len(data)}")
    return info1, idx_len, body_len


def parse_index(data, idx_len, count, start):
    """Parse `count` entries from index offset `start`."""
    idx = data[14:14 + idx_len]
    q = start
    entries = []
    for _ in range(count):
        if q + 4 > len(idx):
            raise ValueError("index truncated at name length")
        n = u32(idx, q)
        q += 4
        if n == 0 or n > 4096 or q + n + 8 > len(idx):
            raise ValueError(f"bad name length {n}")
        raw = idx[q:q + n]
        q += n
        name = raw.decode("utf-8").lstrip("/")
        if not name or "\x00" in name:
            raise ValueError("empty or NUL-containing name")
        off = u32(idx, q)
        size = u32(idx, q + 4)
        q += 8
        entries.append((name, off, size))
    if q > len(idx):
        raise ValueError("index overrun")
    return entries


def score_entries(entries, data, base, mode, body_len):
    if not entries:
        return -1
    score = 0
    total = 0
    for name, off, size in entries:
        actual = off if mode == "absolute" else base + off
        if actual < base or actual + size > len(data):
            return -1
        if name.startswith("/") or ".." in name.replace("\\", "/").split("/"):
            return -1
        total += size
        score += 1
        ext = os.path.splitext(name)[1].lower()
        head = data[actual:actual + 64]
        if ext == ".png":
            score += 8 if head.startswith(PNG) else -8
        elif ext in (".json", ".atlas", ".ls", ".lh"):
            score += 6 if head[:1] in (b"{", b"[") else -6
        elif ext == ".js":
            score += 3 if (b"function" in head or b"var " in head or b"define(" in head) else 0
        elif ext in (".mp3", ".ogg", ".wav"):
            score += 2
    if total == body_len:
        score += 20
    elif body_len and abs(total - body_len) <= body_len * 0.01:
        score += 8
    return score


def choose_layout(data, info1, idx_len, body_len):
    base = 14 + idx_len
    candidates = []
    # Variant B: count stored as the first uint32 of the index.
    if idx_len >= 4:
        n = u32(data, 14)
        if 0 < n <= 200000:
            try:
                entries = parse_index(data, idx_len, n, 4)
                candidates.append((n, entries, "index-count"))
            except Exception as e:
                print(f"  index-count variant rejected: {e}")
    # Variant A: count stored in header.info1, index starts at entry 0.
    if 0 < info1 <= 200000:
        try:
            entries = parse_index(data, idx_len, info1, 0)
            candidates.append((info1, entries, "header-info1"))
        except Exception as e:
            print(f"  header-info1 variant rejected: {e}")
    best = None
    for n, entries, count_mode in candidates:
        for mode in ("absolute", "relative"):
            s = score_entries(entries, data, base, mode, body_len)
            if s > 0 and (best is None or s > best[0]):
                best = (s, entries, count_mode, mode)
    if best is None:
        raise ValueError("could not parse index with any known layout")
    _, entries, count_mode, mode = best
    print(f"  layout: count={count_mode}, offsets={mode}, files={len(entries)}")
    return entries, mode


def unpack(path, outdir):
    data = open(path, "rb").read()
    info1, idx_len, body_len = read_header(data)
    entries, mode = choose_layout(data, info1, idx_len, body_len)
    base = 14 + idx_len
    os.makedirs(outdir, exist_ok=True)
    written = 0
    for name, off, size in entries:
        actual = off if mode == "absolute" else base + off
        rel = os.path.normpath(name.lstrip("/").replace("\\", "/"))
        if rel == "." or rel.startswith("../") or os.path.isabs(rel):
            print(f"  skip unsafe path: {name}")
            continue
        dest = os.path.join(outdir, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            f.write(data[actual:actual + size])
        written += 1
    return len(entries), written, sum(s for _, _, s in entries)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    src = sys.argv[1]
    if os.path.isdir(src):
        files = [os.path.join(src, f) for f in sorted(os.listdir(src)) if f.endswith(".wxapkg")]
        root = sys.argv[2] if len(sys.argv) > 2 else os.path.join("unpacked")
    else:
        files = [src]
        root = sys.argv[2] if len(sys.argv) > 2 else os.path.join("unpacked", os.path.basename(src)[:-7])
    failed = 0
    for path in files:
        name = os.path.basename(path)[:-7]
        outdir = os.path.join(root, name) if os.path.isdir(src) else root
        print(f"{os.path.basename(path)} -> {outdir}")
        try:
            total, written, bytesum = unpack(path, outdir)
            print(f"  ok: {written}/{total} files, {bytesum} bytes")
        except Exception as e:
            failed += 1
            print(f"  FAILED: {e}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())