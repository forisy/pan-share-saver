# PanShareSaver

基于 FastAPI + Playwright 的网盘分享链接一键转存服务，目前内置对百度网盘分享链接的支持。

## 功能
- 扫码登录百度网盘并持久化登录态（Playwright `storage_state`）
- 接收分享链接并在指定网盘目录下执行“保存到网盘”操作
- 简单 REST API：`/login/qr`、`/login/status`、`/transfer`

## 目录结构
```
app/
  adapters/         # 网盘适配器（当前支持 Baidu）
  browser.py        # Playwright 管理器
  config.py         # 环境变量与配置
  main.py           # FastAPI 入口与路由
  schemas.py        # 请求/响应模型
storage/
  baidu_state.json  # 登录态（默认路径，可配置）
Dockerfile
docker-compose.yml
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
- 登录态会持久化在宿主机的 `./storage/baidu_state.json`

## 环境变量
- `HEADLESS`：是否无头浏览器运行，默认 `true`
- `STORAGE_DIR`：登录态存储目录，默认 `storage`
- `BAIDU_TARGET_FOLDER`：转存目标文件夹名，默认 `` 根目录
  - 实际定位路径为 `BAIDU_NODE_PATH = "/{BAIDU_TARGET_FOLDER}"`

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
    {"session_id":"<uuid>","image_base64":"...","expires_in":180}
    ```
- 轮询登录状态
  - 请求：`POST /login/status?provider=baidu&session_id=<uuid>`
  - 返回：`{"status":"pending|success|expired|not_found"}`
- 转存分享链接
  - 请求：`POST /transfer`
  - 请求体：
    ```json
    { "link": "https://pan.baidu.com/s/17jH3_4ub8LxD0LrKxx3-mg?pwd=5pqb" }
    ```
  - 返回：
    ```json
    {
      "status": "success",
      "provider": "baidu",
      "share_link": "https://pan.baidu.com/s/xxxx",
      "target_path": null,
      "message": "transferred"
    }
    ```
  - 注意：若未登录，接口会返回失败并提示先扫码登录

## 运行说明与行为
- 二维码会在约 180 秒内有效；登录成功后会在 `STORAGE_DIR/baidu_state.json` 生成/更新登录态
- 转存时会尝试打开分享链接并点击“保存到网盘”，定位到 `BAIDU_TARGET_FOLDER` 对应目录后确认
- Windows 环境已在应用内部设置事件循环策略，无需额外处理

## 常见问题
- Playwright 浏览器未安装：执行 `python -m playwright install chromium`
- 无法显示二维码或元素定位异常：确保网络正常，必要时将 `HEADLESS=false` 以便观察页面行为

## 许可
本项目仅用于学习与个人使用，请遵循相关平台使用协议与法律法规。