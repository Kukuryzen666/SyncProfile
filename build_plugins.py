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
    ]

    for p in plugins:
        if not os.path.exists(p):
            print(f"Error: {p} not found!", file=sys.stderr)
            sys.exit(1)
        py_compile.compile(p, doraise=True)
        print(f"Verified OK: {os.path.basename(p)} ({os.path.getsize(p)} bytes)")

    # Provide sync.plugin as universal build
    import shutil
    shutil.copyfile(os.path.join(root, "sync_exteragram.plugin"), os.path.join(root, "sync.plugin"))
    py_compile.compile(os.path.join(root, "sync.plugin"), doraise=True)
    print(f"Verified OK: sync.plugin ({os.path.getsize(os.path.join(root, 'sync.plugin'))} bytes)")

if __name__ == "__main__":
    main()

