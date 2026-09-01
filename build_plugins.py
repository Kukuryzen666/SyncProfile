# -*- coding: utf-8 -*-
"""Скрипт валидации версий плагина:
- sync_ayugram.plugin (для клиентов AyuGram)
- sync_exteragram.plugin (для клиентов exteraGram)
"""
import os
import py_compile
import sys

def main():
    root = os.path.dirname(os.path.abspath(__file__))
    plugins = [
        os.path.join(root, "sync_ayugram.plugin"),
        os.path.join(root, "sync_exteragram.plugin"),
        os.path.join(root, "zwylib.plugin"),
    ]

    for p in plugins:
        if not os.path.exists(p):
            print(f"Error: {p} not found!", file=sys.stderr)
            sys.exit(1)
        py_compile.compile(p, doraise=True)
        print(f"Verified OK: {os.path.basename(p)} ({os.path.getsize(p)} bytes)")

if __name__ == "__main__":
    main()

