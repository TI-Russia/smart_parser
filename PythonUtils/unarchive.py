# -*- coding: utf-8 -*-

"""
Tool for proper cyrillic name unarchiving.
Usage:
    python unarchive.py filename.zip
"""

import os
import shutil
import chardet
import zipfile
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("filename")
args = parser.parse_args()

folder, _ = os.path.splitext(args.filename)
if not os.path.isdir(folder):
    os.makedirs(folder)

with zipfile.ZipFile(args.filename, 'r') as brokenzip:
    for name in brokenzip.namelist():
        if not name:
            continue

        if name.endswith("/"):
            os.makedirs(os.path.join(folder, name))
            continue

        fp = brokenzip.open(name)

        res = chardet.detect(name)
        if res['confidence'] > 0.1:
            if res['encoding'] == 'IBM866':
                name = name.decode(res['encoding'])

        fp_out = file(os.path.join(folder, name), 'wb')
        shutil.copyfileobj(fp, fp_out)
        fp.close()
        fp_out.close()
