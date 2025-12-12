import os

HEADLESS = os.getenv("HEADLESS", "true").lower() in {"1", "true", "yes"}
STORAGE_DIR = os.getenv("STORAGE_DIR", "storage")
BAIDU_TARGET_FOLDER = os.getenv("BAIDU_TARGET_FOLDER", "")
BAIDU_NODE_PATH = f"/{BAIDU_TARGET_FOLDER}"
ALIPAN_TARGET_FOLDER = os.getenv("ALIPAN_TARGET_FOLDER", "")
ALIPAN_NODE_PATH = f"/{ALIPAN_TARGET_FOLDER}"
BAIDU_USER_DATA_DIR = os.path.join(STORAGE_DIR, "baidu_userdata")
ALIPAN_USER_DATA_DIR = os.path.join(STORAGE_DIR, "alipan_userdata")
JUEJIN_USER_DATA_DIR = os.path.join(STORAGE_DIR, "juejin_userdata")
V2EX_USER_DATA_DIR = os.path.join(STORAGE_DIR, "v2ex_userdata")
PTFANS_USER_DATA_DIR = os.path.join(STORAGE_DIR, "ptfans_userdata")
TASKS_CONFIG_PATH = os.path.join(STORAGE_DIR, "config")
