# PanShareSaver

基于 FastAPI + Playwright 的网盘分享链接一键转存服务，当前支持百度网盘与阿里云盘（Alipan）分享链接。

## 功能
- 扫码登录并持久化登录态（Playwright `user_data_dir`，支持"按账号隔离"）
- 支持百度网盘与阿里云盘分享链接转存
- REST API：
  - `GET /login/qr`（支持 `provider` 与 `account`，可直接返回 PNG）
  - `POST /transfer`
  - `POST /tasks/*`（定时任务调度，支持 `provider` 与 `accounts` 列表和 `cookies` 字段）
  - `GET /login/vnc`（支持 `provider` 与 `account`，重定向到 Web VNC 页面）
  - `GET /adapters/enabled`（列出已启用的存储适配器与提供者）
  - `GET /tasks/enabled`（列出已启用的任务与已调度任务）

## 目录结构
```
app/
  adapters/         # 网盘适配器（当前支持 Baidu, Alipan）
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
  alipan_userdata # 登录态（默认路径，可配置）
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
- `ALIPAN_TARGET_FOLDER`：转存目标文件夹名，默认空字符串（根目录）
  - 实际定位路径为 `ALIPAN_NODE_PATH = "/{ALIPAN_TARGET_FOLDER}"`
- `TASKS_CONFIG_PATH`：任务配置文件夹路径，默认 `app/config`。也可设置为 `storage/config` 以实现外部持久化管理。

## Cookie 支持

### 1. Cookie 配置格式
本项目支持多种 Cookie 格式，可以灵活配置：

**字符串格式（分号分隔）：**
```json
"cookies": "BDUSS=your_bduss_value; STOKEN=your_stoken_value; other_cookie=other_value"
```

**JSON 对象格式：**
```json
"cookies": {
  "domain.com": {
    "cookie_name": "cookie_value",
    "other_cookie": "other_value"
  }
}
```

**JSON 数组格式（Playwright 原生）：**
```json
"cookies": [
  {
    "name": "cookie_name",
    "value": "cookie_value",
    "domain": "domain.com",
    "path": "/",
    "httpOnly": false,
    "secure": true
  }
]
```

### 2. Cookie 配置方式

#### 任务配置文件 `tasks.json`
在任务配置中直接设置 cookies 字段：

```json
{
  "tasks": [
    {
      "name": "baidu_demo_with_cookies",
      "adapter": "demo",
      "provider": "baidu",
      "cookies": {
        "baidu.com": {
          "BDUSS": "your_bduss_value",
          "STOKEN": "your_stoken_value"
        }
      },
      "schedule": {
        "type": "cron",
        "crontab": "0 9 * * *"
      }
    }
  ]
}
```

#### 传输 API
在转存 API 请求中传递 cookies：

```bash
curl -X POST "http://localhost:8000/transfer" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://pan.baidu.com/s/xxxx",
    "account": "my_account",
    "cookies": "BDUSS=your_bduss_value; STOKEN=your_stoken_value"
  }'
```

或者使用 JSON 对象格式：
```bash
curl -X POST "http://localhost:8000/transfer" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://pan.baidu.com/s/xxxx",
    "account": "my_account",
    "cookies": {
      "baidu.com": {
        "BDUSS": "your_bduss_value",
        "STOKEN": "your_stoken_value"
      }
    }
  }'
```

#### 任务调度 API
在通过 API 调度任务时，也可以传递 cookies 参数：

**定时任务 API 示例：**
```bash
curl -X POST "http://localhost:8000/tasks/run_now" \
  -H "Content-Type: application/json" \
  -d '{
    "adapter": "demo",
    "provider": "baidu",
    "accounts": ["my_account"],
    "cookies": {
      "baidu.com": {
        "BDUSS": "your_bduss_value",
        "STOKEN": "your_stoken_value"
      }
    }
  }'
```

### Cookie 格式说明
- **字符串格式**：使用分号分隔的 "key=value" 对，例如 `"cookie1=value1; cookie2=value2"`
- **JSON 对象格式**：以域名作为键，域名下的 cookie 键值对作为值
- **JSON 数组格式**：完全兼容 Playwright 的 cookie 设置格式，包含 name、value、domain、path 等字段

### 使用建议
1. **安全性**：Cookie 包含敏感登录信息，请妥善保管，避免泄露
2. **时效性**：Cookie 有过期时间，需要定期更新
3. **兼容性**：建议使用 JSON 对象格式，兼容性最好
4. **调试**：如果 Cookie 登录失败，可以先尝试手动登录获取最新的 Cookie

## 任务调度与配置

### 配置字段表

**任务级字段**

| 字段 | 别名 | 类型 | 必需 | 说明 |
|------|------|-----|------|------|
| `name` | `id` | string | 否 | 任务名称，作为 `job_id` 使用，不设置时自动生成 |
| `entry` | `adapter` | string | 是 | 执行入口，对应已注册的 `TaskAdapter` 名称 |
| `provider` | `provider_name` | string | 否 | 任务执行的适配器提供者 |
| `accounts` | - | array | 否 | 账号列表，用于按账号隔离用户数据目录并逐账号执行 |
| `cookies` | - | string/object/array | 否 | Cookie 配置，支持多种格式 |

**调度字段**

| 字段 | 别名 | 类型 | 说明 | 示例 |
|------|------|-----|------|------|
| `type` | `kind` | string | 调度类型（`cron`/`date`/`between`/`window`） | `"cron"` |
| `crontab` | - | string | 标准 5 段 crontab 格式 | `"0 9 * * *"` |
| `fields` | - | object | 对象形式的 cron 字段 | `{"minute": "0", "hour": "9"}` |
| `second`/`minute`/`hour`/`day`/`month`/`day_of_week` | - | string | 直接的 cron 字段 | `"0"` |
| `run_at` | `at` | string | ISO 8601 日期时间（date 类型） | `"2025-12-31T09:00:00"` |
| `start_at` | `start` | string | 开始时间（between 类型） | `"2025-12-31T08:00:00"` |
| `end_at` | `end` | string | 结束时间（between 类型） | `"2025-12-31T09:00:00"` |
| `base_at` | `at` | string | 基准时间（window 类型） | `"2025-12-31T08:00:00"` |
| `window_minutes` | `window` | number | 时间窗口（分钟） | `60` |

**Cookie 格式说明**

| 格式 | 示例 | 说明 |
|------|------|------|
| 字符串 | `"cookie1=value1; cookie2=value2"` | 分号分隔的键值对 |
| JSON 对象 | `{"domain.com": {"name": "value"}}` | 以域名分组的 Cookie 键值对 |
| JSON 数组 | `[{"name": "n", "value": "v", ...}]` | Playwright 原生 Cookie 格式 |

**支持的 TaskAdapter 列表**
- `demo` - 示例任务适配器
- `juejin_signin` - 掘金签到任务
- `v2ex_signin` - V2EX 签到任务  
- `ptfans_signin` - PTFans 签到任务

**支持的 Provider 列表**
- `baidu`, `alipan`, `juejin`, `v2ex`, `ptfans`

### 配置示例

**完整的 tasks.json 结构：**
```json
{
  "tasks": [
    {
      "name": "demo_hourly",
      "entry": "demo",
      "provider": "baidu",
      "accounts": ["accA", "accB"],
      "cookies": {
        "baidu.com": {
          "BDUSS": "your_bduss_value",
          "STOKEN": "your_stoken_value"
        }
      },
      "schedule": { "type": "cron", "crontab": "0 * * * *" }
    },
    {
      "name": "demo_once",
      "entry": "demo",
      "provider": "alipan",
      "accounts": ["accX"],
      "cookies": "PDSM_ARTIFACT=your_alipan_cookie_value",
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
      "provider": "alipan",
      "accounts": ["default"],
      "cookies": [
        {
          "name": "cookie_name",
          "value": "cookie_value",
          "domain": "alipan.com",
          "path": "/",
          "httpOnly": false,
          "secure": true
        }
      ],
      "schedule": { "type": "window", "base_at": "2025-12-10T08:00:00", "window_minutes": 30 }
    }
  ]
}
```

### 详细配置说明

1. **基本任务配置**（最简单的定时任务）
```json
{
  "tasks": [
    {
      "entry": "juejin_signin",
      "provider": "juejin",
      "schedule": "0 8 * * *"
    }
  ]
}
```
- 使用简化的 crontab 字符串格式
- 任务名称自动生成
- 无账号隔离，使用默认账号

2. **多账号轮询任务**
```json
{
  "tasks": [
    {
      "name": "v2ex_daily_checkin",
      "adapter": "v2ex_signin",
      "provider": "v2ex",
      "accounts": ["user1", "user2", "user3"],
      "schedule": {
        "type": "cron",
        "fields": {
          "minute": "0",
          "hour": "9"
        }
      }
    }
  ]
}
```
- 使用 `accounts` 数组为每个账号独立执行任务
- 账号数据隔离存储在 `storage/v2ex_userdata/<account_name>/`

3. **Cookie 驱动任务**
```json
{
  "tasks": [
    {
      "id": "alipan_transfer_task",  // 也可以使用 id 替代 name
      "entry": "demo",
      "provider_name": "alipan",    // 也可以使用 provider_name 替代 provider
      "cookies": {
        "alipan.com": {
          "authorization": "Bearer your_token",
          "refreshToken": "your_refresh_token"
        }
      },
      "schedule": {
        "kind": "cron",             // 也可以使用 kind 替代 type
        "crontab": "30 7 * * *"
      }
    }
  ]
}
```
- 使用 JSON 对象格式的 cookies
- 支持字段别名（id/name, entry/adapter, provider/provider_name, kind/type）

4. **时间窗口任务**
```json
{
  "tasks": [
    {
      "name": "random_checkin_window",
      "entry": "ptfans_signin", 
      "provider": "ptfans",
      "schedule": {
        "type": "window",
        "base_at": "2025-12-31T08:00:00",    // 基准时间
        "window": 60                         // 60分钟窗口内随机执行
      }
    }
  ]
}
```
- 在指定基准时间后的 60 分钟窗口内随机选择执行时间
- 使用 `window` 替代 `window_minutes`（别名支持）

5. **时间段随机任务**
```json
{
  "tasks": [
    {
      "name": "random_checkin_between",
      "entry": "juejin_signin",
      "provider": "juejin", 
      "schedule": {
        "type": "between",
        "start": "2025-12-31T07:00:00",     // 开始时间
        "end": "2025-12-31T09:00:00"        // 结束时间
      }
    }
  ]
}
```
- 在指定时间段内随机选择执行时间
- 使用 `start`/`end` 替代 `start_at`/`end_at`（别名支持）

6. **单次执行任务**
```json
{
  "tasks": [
    {
      "name": "one_time_cleanup",
      "entry": "demo",
      "provider": "baidu",
      "accounts": ["main_account"],
      "cookies": "BDUSS=your_value; STOKEN=your_value",  // 字符串格式 cookies
      "schedule": {
        "type": "date",
        "at": "2025-12-31T23:59:59"        // 使用 at 替代 run_at
      }
    }
  ]
}
```
- 只执行一次的特定时间任务
- Cookie 使用字符串格式

7. **复杂 Cron 任务**
```json
{
  "tasks": [
    {
      "name": "complex_cron_task",
      "entry": "demo",
      "provider": "alipan",
      "schedule": {
        "type": "cron",
        "minute": "30",           // 每小时的 30 分
        "hour": "*/2",            // 每 2 小时
        "day": "1,15",            // 每月 1 号和 15 号
        "month": "1-12",          // 每月
        "day_of_week": "0-4"      // 周一到周五
      }
    }
  ]
}
```
- 使用详细的 cron 字段格式
- 支持复杂的调度规则

8. **Playwright Cookie 格式任务**
```json
{
  "tasks": [
    {
      "name": "playwright_cookie_task",
      "entry": "demo",
      "provider": "baidu",
      "cookies": [
        {
          "name": "BDUSS",
          "value": "your_bduss_value",
          "domain": ".baidu.com",
          "path": "/",
          "expires": 2147483647,
          "httpOnly": true,
          "secure": true
        },
        {
          "name": "STOKEN",
          "value": "your_stoken_value", 
          "domain": ".baidu.com",
          "path": "/",
          "expires": 2147483647,
          "httpOnly": true,
          "secure": true
        }
      ],
      "schedule": {
        "type": "cron",
        "crontab": "0 0 * * *"
      }
    }
  ]
}
```
- 使用 Playwright 原生的 Cookie 数组格式
- 包含完整的 Cookie 属性（expires, httpOnly, secure 等）

## API 使用

### 基础功能 API

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
  - 注意：此 API 需要手动实现（当前系统自动处理登录状态检测）

- 打开 Web VNC 页面
  - 请求：`GET /login/vnc`
  - 行为：重定向至 `http://localhost:6080/vnc.html?autoconnect=true&resize=scale&view_clip=true`

- 转存分享链接
  - 请求：`POST /transfer`
  - 请求体：
    ```json
    { 
      "url": "https://pan.baidu.com/s/17jH3_4ub8LxD0LrKxx3-mg?pwd=5pqb",
      "account": "my_account",
      "cookies": {
        "baidu.com": {
          "BDUSS": "your_bduss_value",
          "STOKEN": "your_stoken_value"
        }
      }
    }
    ```
    或者使用 Cookie 字符串格式：
    ```json
    { 
      "url": "https://pan.baidu.com/s/17jH3_4ub8LxD0LrKxx3-mg?pwd=5pqb",
      "account": "my_account",
      "cookies": "BDUSS=your_bduss_value; STOKEN=your_stoken_value"
    }
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
    或者 Cookie 相关错误：
    ```json
    {
      "status": "error",
      "provider": "baidu",
      "share_link": "https://pan.baidu.com/s/xxxx",
      "message": "transfer_not_implemented"
    }
    ```
  - 注意：
    - `account` 字段用于账号隔离，可选
    - `cookies` 字段用于直接使用 Cookie 登录，可选，支持字符串或 JSON 格式
    - 若未登录且未提供有效 Cookie，接口会返回失败并提示先扫码登录
    - 对于不支持转存功能的适配器（如 V2EX、Juejin、PTFans），将返回 `transfer_not_implemented` 错误

- 列出启用的适配器
  - 请求：`GET /adapters/enabled`
  - 示例返回：
    ```json
    {
      "providers": ["alipan", "aliyundrive", "baidu", "baidupan", "juejin"],
      "adapters": ["alipan", "baidu", "juejin"]
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

### 任务调度 API

#### 立即运行任务
- 请求：`POST /tasks/run_now`
- 请求体：
  ```json
  {
    "adapter": "demo",
    "provider": "baidu",
    "accounts": ["my_account"],
    "cookies": {
      "baidu.com": {
        "BDUSS": "your_bduss_value",
        "STOKEN": "your_stoken_value"
      }
    }
  }
  ```
- 返回：
  ```json
  {
    "status": "success",
    "adapter": "demo",
    "message": null
  }
  ```

#### 定时调度任务（单次执行）
- 请求：`POST /tasks/schedule_at`
- 请求体：
  ```json
  {
    "adapter": "demo",
    "run_at": "2025-12-31T09:00:00",
    "provider": "baidu",
    "accounts": ["my_account"],
    "cookies": "BDUSS=your_bduss_value; STOKEN=your_stoken_value"
  }
  ```

#### 定时调度任务（在时间段内随机执行）
- 请求：`POST /tasks/schedule_between`
- 请求体：
  ```json
  {
    "adapter": "demo",
    "start_at": "2025-12-31T08:00:00",
    "end_at": "2025-12-31T09:00:00",
    "provider": "baidu",
    "accounts": ["my_account"],
    "cookies": [
      {
        "name": "BDUSS",
        "value": "your_bduss_value",
        "domain": "baidu.com",
        "path": "/",
        "httpOnly": true,
        "secure": true
      }
    ]
  }
  ```

#### 定时调度任务（时间窗口内随机执行）
- 请求：`POST /tasks/schedule_window`
- 请求体：
  ```json
  {
    "adapter": "demo",
    "base_at": "2025-12-31T08:30:00",
    "window_minutes": 30,
    "provider": "baidu",
    "accounts": ["my_account"],
    "cookies": {
      "baidu.com": {
        "BDUSS": "your_bduss_value",
        "STOKEN": "your_stoken_value"
      }
    }
  }
  ```

### 启动行为
- 服务启动后会自动调用配置加载并注册定时任务，无需额外 API 操作。

## 运行说明与行为
- 二维码会在约 180 秒内有效；登录成功后会在 `STORAGE_DIR/<provider>_userdata` 生成/更新登录态
- 多账号隔离：当传入 `account` 时，登录态与浏览器缓存会持久化到 `STORAGE_DIR/<provider>_userdata/<account>` 子目录；未传入则使用默认目录
- 应用启动后会运行后台队列处理器；`POST /transfer` 仅入队并立即返回，实际转存过程在后台执行
- 转存时会尝试打开分享链接并点击"保存到网盘"，定位到 `BAIDU_TARGET_FOLDER`/`ALIPAN_TARGET_FOLDER` 对应目录后确认
- Windows 环境已在应用内部设置事件循环策略，无需额外处理

## 常见问题
- Playwright 浏览器未安装：执行 `python -m playwright install chromium`
- 无法显示二维码或元素定位异常：确保网络正常，必要时将 `HEADLESS=false` 以便观察页面行为
- VNC 页面无法打开：请确认以 `docker-compose-vnc.yml` 模式运行并开放 `6080/5900` 端口

## 许可
本项目仅用于学习与个人使用，请遵循相关平台使用协议与法律法规。