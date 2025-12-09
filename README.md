# PanShareSaver

基于 FastAPI + Playwright 的网盘分享链接一键转存服务，当前支持百度网盘与阿里云盘分享链接。

## 功能
- 扫码登录并持久化登录态（Playwright 持久化用户数据目录 `user_data_dir`）
- 支持百度网盘与阿里云盘分享链接转存
- 简单 REST API：`/login/qr`、`/login/status`、`/transfer`（支持 `provider` 选择）

## 目录结构
```
app/
  adapters/         # 网盘适配器（当前支持 Baidu）
  browser.py        # Playwright 管理器
  config.py         # 环境变量与配置
  main.py           # FastAPI 入口与路由
  schemas.py        # 请求/响应模型
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

### VNC 显示与自适应
- noVNC 支持本地缩放与远端分辨率调整：
  - `resize=scale`：按浏览器窗口缩放显示（推荐，兼容性最好）。
  - `resize=remote`：请求服务端调整桌面分辨率（需 VNC 服务器支持 SetDesktopSize/ExtendedDesktopSize）。
- 当前镜像使用 `x11vnc + Xvfb`，默认固定分辨率 `1280x800`；通常推荐 `resize=scale` 达到自适应效果。

## API 使用
- 获取扫码登录二维码
  - 请求：
    - `GET /login/qr?provider=baidu&as_image=true` 返回 PNG 图片
    - `GET /login/qr?provider=baidu&as_image=false` 返回 base64 字符串与 `session_id`
  - 示例：
    ```bash
    curl "http://localhost:8000/login/qr?provider=baidu&as_image=false"
    ```
  - 返回：
    ```json
    {"session_id":"<uuid>","image_base64":"...","expires_in":180,"islogin":false}
    ```
  - 说明：当 `as_image=true` 且当前未登录时，接口直接返回二维码 PNG 图片；若已登录则返回 `islogin=true` 的 JSON。
- 轮询登录状态
  - 请求：`POST /login/status?provider=baidu&session_id=<uuid>`
  - 返回：`{"status":"pending|success|expired|not_found"}`
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

## 运行说明与行为
- 二维码会在约 180 秒内有效；登录成功后会在 `STORAGE_DIR/baidu_userdata` 生成/更新登录态
- 应用启动后会运行后台队列处理器；`POST /transfer` 仅入队并立即返回，实际转存过程在后台执行
- 转存时会尝试打开分享链接并点击“保存到网盘”，定位到 `BAIDU_TARGET_FOLDER`/`ALIYUN_TARGET_FOLDER` 对应目录后确认
- Windows 环境已在应用内部设置事件循环策略，无需额外处理

## 常见问题
- Playwright 浏览器未安装：执行 `python -m playwright install chromium`
- 无法显示二维码或元素定位异常：确保网络正常，必要时将 `HEADLESS=false` 以便观察页面行为

## 许可
本项目仅用于学习与个人使用，请遵循相关平台使用协议与法律法规。
