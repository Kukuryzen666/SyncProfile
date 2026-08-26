import os

root_dir = os.path.dirname(os.path.abspath(__file__))
src = os.path.join(root_dir, "sync_profile.py")
dst_full = os.path.join(root_dir, "sync_profile.plugin")
dst_locked = os.path.join(root_dir, "sync.plugin")

with open(src, "r", encoding="utf-8") as f:
    code = f.read()

code_full = code.replace("ALLOW_CUSTOM_SERVER_CONFIG = False", "ALLOW_CUSTOM_SERVER_CONFIG = True")
if "ALLOW_CUSTOM_SERVER_CONFIG = True" not in code_full:
    code_full = code_full.replace('COOKIE_NAME = "sync_access"\n', 'COOKIE_NAME = "sync_access"\nALLOW_CUSTOM_SERVER_CONFIG = True\n')
    code_full = code_full.replace("COOKIE_NAME = 'sync_access'\n", "COOKIE_NAME = 'sync_access'\nALLOW_CUSTOM_SERVER_CONFIG = True\n")

with open(dst_full, "w", encoding="utf-8") as f:
    f.write(code_full)

code_locked = code_full.replace("ALLOW_CUSTOM_SERVER_CONFIG = True", "ALLOW_CUSTOM_SERVER_CONFIG = False")

with open(dst_locked, "w", encoding="utf-8") as f:
    f.write(code_locked)

print("Plugins built successfully:")
print("  - sync_profile.plugin [Full: Custom URL & Auth enabled]")
print("  - sync.plugin         [Simple/Locked: Fixed URL & Auth hidden]")
