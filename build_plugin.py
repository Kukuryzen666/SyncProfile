import re
src_file = "sync_profile.py"
with open(src_file, "r", encoding="utf-8") as f:
    content = f.read()
selfhosted_content = re.sub(
    r"^ALLOW_CUSTOM_SERVER_CONFIG\s*=\s*(?:False|True)",
    "ALLOW_CUSTOM_SERVER_CONFIG = True",
    content, flags=re.MULTILINE
)
with open("sync_profile.plugin", "w", encoding="utf-8") as f:
    f.write(selfhosted_content)
simple_content = re.sub(
    r"^ALLOW_CUSTOM_SERVER_CONFIG\s*=\s*(?:False|True)",
    "ALLOW_CUSTOM_SERVER_CONFIG = False",
    content, flags=re.MULTILINE
)
with open("sync.plugin", "w", encoding="utf-8") as f:
    f.write(simple_content)
print("Plugins built successfully.")
