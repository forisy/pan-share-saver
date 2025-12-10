# PanShareSaver

基于 FastAPI + Playwright 的网盘分享链接一键转存服务，当前支持百度网盘与阿里云盘分享链接。

## 功能
- 扫码登录并持久化登录态（Playwright `user_data_dir`，支持“按账号隔离”）
- 支持百度网盘与阿里云盘分享链接转存
- REST API：
  - `GET /login/qr`（支持 `provider` 与 `account`，可直接返回 PNG）
  - `POST /transfer`
  - `POST /tasks/*`（定时任务调度，支持 `provider` 与 `accounts` 列表）
  - `GET /login/vnc`（支持 `provider` 与 `account`，重定向到 Web VNC 页面）
  - `GET /adapters/enabled`（列出已启用的存储适配器与提供者）
  - `GET /tasks/enabled`（列出已启用的任务与已调度任务）

## 目录结构
```
app/
  adapters/         # 网盘适配器（当前支持 Baidu）
  browser.py        # Playwright 管理器
  config.py         # 环境变量与配置
  main.py           # FastAPI 入口与路由
  schemas.py        # 请求/响应模型
  tasks/            # 定时任务调度与配置
    scheduler.py    # APScheduler 封装与配置加载
    registry.py     # 任务适配器注册
    demo.py         # 示例任务
    tasks.json      # 示例配置文件（可复制到 storage/）
storage/
  baidu_userdata  # 登录态（默认路径，可配置）
  aliyun_userdata # 登录态（默认路径，可配置）
Dockerfile
Dockerfile.vnc
docker-compose.yml
docker-compose-vnc.yml
supervisord.conf
start.sh
requirements.txt
```

## 快速开始（本地）
1. 安装 Python 3.11+
2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   python -m playwright install chromium
   ```
3. 启动服务：
   ```bash
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

## 快速开始（Docker）
- 使用 Docker 运行（已包含 Playwright 运行所需依赖）：
  ```bash
  docker compose up -d --build
  ```
- 服务默认监听 `http://localhost:8000`
- 登录态会持久化在宿主机的 `./storage/baidu_userdata`

- 使用带浏览器桌面与 VNC 的模式：
  ```bash
  docker compose -f docker-compose-vnc.yml up -d --build
  ```
  - Web VNC 访问：`http://localhost:6080/vnc.html?autoconnect=true&resize=scale&view_clip=true`
  - 原生 VNC 端口：`5900`
  - 说明：`resize=scale` 让 VNC 画面随浏览器内容区自动缩放；`view_clip=true` 去除滚动条以适配嵌入式布局。

## 环境变量
- `HEADLESS`：是否无头浏览器运行，默认 `true`
- `STORAGE_DIR`：登录态存储目录，默认 `storage`
- `BAIDU_TARGET_FOLDER`：转存目标文件夹名，默认空字符串（根目录）
  - 实际定位路径为 `BAIDU_NODE_PATH = "/{BAIDU_TARGET_FOLDER}"`
- `ALIYUN_TARGET_FOLDER`：转存目标文件夹名，默认空字符串（根目录）
  - 实际定位路径为 `ALIYUN_NODE_PATH = "/{ALIYUN_TARGET_FOLDER}"`
- `TASKS_CONFIG_PATH`：任务配置文件路径，默认 `app/tasks/tasks.json`。也可设置为 `storage/tasks.json` 以实现外部持久化管理。

### VNC 显示与自适应
- noVNC 支持本地缩放与远端分辨率调整：
  - `resize=scale`：按浏览器窗口缩放显示（推荐，兼容性最好）。
  - `resize=remote`：请求服务端调整桌面分辨率（需 VNC 服务器支持 SetDesktopSize/ExtendedDesktopSize）。
- 当前镜像使用 `x11vnc + Xvfb`，默认固定分辨率 `1280x800`；通常推荐 `resize=scale` 达到自适应效果。

## API 使用
- 获取扫码登录二维码
  - 请求：
    - `GET /login/qr?provider=baidu&account=accA&as_image=true` 返回 PNG 图片
    - `GET /login/qr?provider=baidu&account=accA&as_image=false` 返回 base64 与 `session_id`
  - 示例：
    ```bash
    curl "http://localhost:8000/login/qr?provider=baidu&account=accA&as_image=false"
    ```
  - 返回：
    ```json
    {"session_id":"<uuid>","image_base64":"...","expires_in":180,"islogin":false}
    ```
  - 说明：当 `as_image=true` 且当前未登录时，接口直接返回二维码 PNG；若已登录返回 `islogin=true` 的 JSON。
- 轮询登录状态
  - 请求：`POST /login/status?provider=baidu&session_id=<uuid>`
  - 返回：`{"status":"pending|success|expired|not_found"}`
- 打开 Web VNC 页面
  - 请求：`GET /login/vnc`
  - 行为：重定向至 `http://localhost:6080/vnc.html?autoconnect=true&resize=scale&view_clip=true`
- 转存分享链接
  - 请求：`POST /transfer`
  - 请求体：
    ```json
    { "url": "https://pan.baidu.com/s/17jH3_4ub8LxD0LrKxx3-mg?pwd=5pqb" }
    ```
  - 返回：
    ```json
    {
      "status": "accepted",
      "provider": "baidu",
      "share_link": "https://pan.baidu.com/s/xxxx",
      "target_path": null,
      "message": "queued"
    }
    ```
  - 可能返回：
    ```json
    {"status":"ignored","provider":"baidu","share_link":"https://pan.baidu.com/s/xxxx","target_path":null,"message":"duplicate"}
    ```
  - 注意：若未登录，接口会返回失败并提示先扫码登录

- 列出启用的适配器
  - 请求：`GET /adapters/enabled`
  - 示例返回：
    ```json
    {
      "providers": ["aliyun", "alipan", "aliyundrive", "baidu", "baidupan", "juejin"],
      "adapters": ["aliyun", "baidu", "juejin"]
    }
    ```

- 列出启用的任务
  - 请求：`GET /tasks/enabled`
  - 示例返回：
    ```json
    {
      "tasks": ["demo", "juejin_signin"],
      "scheduled_jobs": [
        {
          "job_id": "task:demo:1",
          "adapter": "demo",
          "next_run_time": "2025-12-10T10:00:00"
        }
      ]
    }
    ```

## 任务调度与配置
- 支持通过 JSON 配置文件定义“任务名称/定时规则/执行入口”，应用启动时自动加载。
- 配置文件位置：
  - 默认：`app/tasks/tasks.json`
  - 持久化：将其放至 `storage/tasks.json` 并设置环境变量 `TASKS_CONFIG_PATH=storage/tasks.json`

### 配置示例
```json
{
  "tasks": [
    {
      "name": "demo_hourly",
      "entry": "demo",
      "provider": "baidu",
      "accounts": ["accA", "accB"],
      "schedule": { "type": "cron", "crontab": "0 * * * *" }
    },
    {
      "name": "demo_once",
      "entry": "demo",
      "provider": "aliyun",
      "accounts": ["accX"],
      "schedule": { "type": "date", "run_at": "2025-12-10T10:00:00" }
    },
    {
      "name": "demo_between",
      "entry": "demo",
      "provider": "baidu",
      "accounts": ["accA"],
      "schedule": { "type": "between", "start_at": "2025-12-10T08:00:00", "end_at": "2025-12-10T09:00:00" }
    },
    {
      "name": "demo_window",
      "entry": "demo",
      "provider": "aliyun",
      "accounts": ["default"],
      "schedule": { "type": "window", "base_at": "2025-12-10T08:00:00", "window_minutes": 30 }
    }
  ]
}
```

### 字段说明
- 任务级：
  - `name`：任务名称（作为 `job_id` 使用，可选）
  - `entry`/`adapter`：执行入口，对应已注册的 `TaskAdapter` 名称（当前示例为 `demo`）
  - `provider`：任务执行的网盘适配器（`baidu`/`aliyun`）
  - `accounts`：账号列表（可选），用于按账号隔离用户数据目录并逐账号执行
- `schedule`：调度规则（`type` 支持以下四种）：
  - `cron`：支持 `crontab`（5 段）或字段 `second|minute|hour|day|month|day_of_week`
  - `date`：单次执行，需 `run_at`（ISO 8601）
  - `between`：在 `start_at` 与 `end_at` 之间随机选择时间执行
  - `window`：在窗口内随机执行，需 `base_at` 与 `window_minutes`

### 启动行为
- 服务启动后会自动调用配置加载并注册定时任务，无需额外 API 操作。

## 运行说明与行为
- 二维码会在约 180 秒内有效；登录成功后会在 `STORAGE_DIR/<provider>_userdata` 生成/更新登录态
- 多账号隔离：当传入 `account` 时，登录态与浏览器缓存会持久化到 `STORAGE_DIR/<provider>_userdata/<account>` 子目录；未传入则使用默认目录
- 应用启动后会运行后台队列处理器；`POST /transfer` 仅入队并立即返回，实际转存过程在后台执行
- 转存时会尝试打开分享链接并点击“保存到网盘”，定位到 `BAIDU_TARGET_FOLDER`/`ALIYUN_TARGET_FOLDER` 对应目录后确认
- Windows 环境已在应用内部设置事件循环策略，无需额外处理

## 常见问题
- Playwright 浏览器未安装：执行 `python -m playwright install chromium`
- 无法显示二维码或元素定位异常：确保网络正常，必要时将 `HEADLESS=false` 以便观察页面行为
- VNC 页面无法打开：请确认以 `docker-compose-vnc.yml` 模式运行并开放 `6080/5900` 端口

## 许可
本项目仅用于学习与个人使用，请遵循相关平台使用协议与法律法规。
