#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division

MAX_COMPRESSIBILITY = 0.7
CHUNK_SIZE = 1*1024

import os, sys, lzo, string, mimetypes
import subprocess as sp
from os.path import isdir, isfile, join, abspath

COMPRESSIBLE_MIMES = ["application/x-sh",
                      "application/postscript",
                      "application/x-perl",
                      "application/x-awk",
                      "application/x-javascript",
                      "application/rtf"]

COMPRESSED_MIMES  =  ["application/x-par2",
                      "application/x-cpio",
                      "application/x-shar",
                      "application/x-tar",
                      "application/x-bzip2",
                      "application/x-gzip",
                      "application/x-lzip",
                      "application/x-lzma",
                      "application/x-lzop",
                      "application/x-xz",
                      "application/x-compress",
                      "application/x-7z-compressed",
                      "application/x-ace-compressed",
                      "application/x-astrotite-afa",
                      "application/x-alz-compressed",
                      "application/vnd.android.package-archive",
                      "application/x-arj",
                      "application/x-b1",
                      "application/vnd.ms-cab-compressed",
                      "application/x-cfs-compressed",
                      "application/x-dar",
                      "application/x-dgc-compressed",
                      "application/x-apple-diskimage",
                      "application/x-gca-compressed",
                      "application/x-lzh",
                      "application/x-lzx",
                      "application/x-rar-compressed",
                      "application/x-stuffit",
                      "application/x-stuffitx",
                      "application/x-gtar",
                      "application/zip",
                      "application/x-zoo"]

def compressible_mime(fname):
    t = str(mimetypes.guess_type(fname)[0])
    if t.startswith("text"):
        return True
    elif t in COMPRESSIBLE_MIMES:
        return True
    elif t.startswith("audio") or t.startswith("video") or t.startswith("image"):
        return "never"
    elif t in COMPRESSED_MIMES:
        return "never"
    return False

def istext(filename):
    with open(filename, "rt") as f:
        s = f.read(512)
    text_characters = "".join(map(chr, range(32, 127)) + list("\n\r\t\b"))
    _null_trans = string.maketrans("", "")
    if not s:
        # Empty files are considered text
        return True
    if "\0" in s:
        # Files with null bytes are likely binary
        return False
    # Get the non-text characters (maps a character to itself then
    # use the 'remove' option to get rid of the text characters.)
    t = s.translate(_null_trans, text_characters)
    # If more than 30% non-text characters, then
    # this is considered a binary file
    if float(len(t))/float(len(s)) > 0.30:
        return False
    return True

def compression_factor(chunk):
    l1 = len(chunk)
    l2 = len(lzo.compress(chunk))
    return float(l2)/l1

def estimate_compressibility(path):
    with open(path, "rb") as f:
        f.seek(-1, 2)
        size = f.tell()
        if size < CHUNK_SIZE:
            return compression_factor(f.read())
        else:
            f.seek(size/2 - CHUNK_SIZE / 2)
            return compression_factor(f.read(CHUNK_SIZE))

def already_compressed(path):
    try:
        out = sp.check_output(["lsattr", path])
        if "c" in out:
            return True
        return False
    except Exception:
        import traceback; traceback.print_exc();
        return False

def btrfs_compress(path):
    p = sp.Popen(["chattr", "+c", path])
    p.wait()
    p = sp.Popen(["btrfs", "filesystem", "defragment", "-c", path])
    p.wait()

def scan_path(path):
    path = abspath(path)
    for i in os.listdir(path):
        f = join(path, i)
        if "ccache" in f:
            continue
        if isdir(f):
            scan_path(f)
        elif isfile(f):
            if already_compressed(f):
                #print "Not compressing", f, ", compress attribute already set"
                continue
            m = compressible_mime(f)
            if m == "never":
                print "Not compressing", f, ", bad MIME"
                continue
            elif not m:
                if not istext(f):
                    compressibility = estimate_compressibility(f)
                    if compressibility > MAX_COMPRESSIBILITY:
                        print "Not compressing", f, ", compressibility ==", compressibility
                        continue

            print "Compressing", f
            btrfs_compress(f)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Please provide at least one path.")
    for p in sys.argv[1:]:
        scan_path(p)