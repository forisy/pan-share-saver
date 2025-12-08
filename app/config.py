import os

HEADLESS = os.getenv("HEADLESS", "false").lower() in {"1", "true", "yes"}
STORAGE_DIR = os.getenv("STORAGE_DIR", "storage")
BAIDU_STORAGE_STATE = os.path.join(STORAGE_DIR, "baidu_state.json")
BAIDU_TARGET_FOLDER = os.getenv("BAIDU_TARGET_FOLDER", "")
BAIDU_NODE_PATH = f"/{BAIDU_TARGET_FOLDER}"
ALIYUN_STORAGE_STATE = os.path.join(STORAGE_DIR, "aliyun_state.json")
ALIYUN_TARGET_FOLDER = os.getenv("ALIYUN_TARGET_FOLDER", "")
ALIYUN_NODE_PATH = f"/{ALIYUN_TARGET_FOLDER}"
BAIDU_USER_DATA_DIR = os.path.join(STORAGE_DIR, "baidu_userdata")
ALIYUN_USER_DATA_DIR = os.path.join(STORAGE_DIR, "aliyun_userdata")
