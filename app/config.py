import os

HEADLESS = os.getenv("HEADLESS", "true").lower() in {"1", "true", "yes"}
STORAGE_DIR = os.getenv("STORAGE_DIR", "storage")
BAIDU_STORAGE_STATE = os.path.join(STORAGE_DIR, "baidu_state.json")
BAIDU_TARGET_FOLDER = os.getenv("BAIDU_TARGET_FOLDER", "")
BAIDU_NODE_PATH = f"/{BAIDU_TARGET_FOLDER}"