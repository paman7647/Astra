import sys
import os

# Set local engine path
LOCAL_ENGINE_PATH = "/Users/paman7647/Downloads/whatsapp-web.js-main"
sys.path.insert(0, LOCAL_ENGINE_PATH)

try:
    from astra.protocol.js_engine import JS_ENGINE_SOURCE
    with open("bridge_check.js", "w") as f:
        f.write(JS_ENGINE_SOURCE)
    print("Bridge source assembled to bridge_check.js")
except Exception as e:
    print(f"Failed to assemble bridge: {e}")
    sys.exit(1)
