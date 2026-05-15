# server-console 项目分析

更新时间：2026-05-15

## 一句话概览

`server-console` 是一个 Flask 后端服务，主要服务于综合后台管理场景：用户登录与用户管理、婚礼照片墙、婚礼音乐、OSS 图片同步、体重管理，以及独立的餐馆菜品管理接口。

## 技术栈

- Web 框架：Flask
- ORM：Flask-SQLAlchemy / SQLAlchemy
- 数据库：PostgreSQL，生产环境连接 Supabase
- 鉴权：Flask-JWT-Extended，JWT 存储在 Cookie 中
- 对象存储：阿里云 OSS，成都区域
- 异步任务：Celery + Redis
- 部署：Docker + Gunicorn + Kubernetes

## 启动链路

入口文件是 `app.py`：

1. 通过 `python-dotenv` 加载 `.env`。
2. 创建 Flask app，并配置 CORS，允许 `https://console.tt829.cn` 和 `http://localhost:5173` 携带 Cookie 跨域访问。
3. 从 `config.py` 加载数据库、JWT、Redis、OSS 配置。
4. 初始化 `db` 和 `jwt`。
5. 注册 `after_request` 钩子，在访问令牌即将过期时刷新 access token。
6. 注册 JWT 错误处理。
7. 通过 `create_missing_tables(app)` 导入所有模型并尝试创建缺失表。
8. 通过 `register_api_blueprints(app)` 自动扫描并注册 `api/*_api.py` 蓝图。
9. 通过 `make_celery(app)` 创建 Celery 实例，并注册任务。
10. 提供 `/health` 健康检查，供 Kubernetes 探针使用。

本地运行：

```bash
python app.py
```

生产镜像使用：

```bash
gunicorn -c gunicorn_config.py app:app
```

## 路由注册规则

`utils/register_api_blueprints.py` 会扫描 `api/` 下所有以 `_api.py` 结尾的文件，并约定每个模块导出 `<module_name>_pb` 蓝图对象。

- `dish_api.py` 注册到 `/api/chuan-dai`
- 其他 API 注册到 `/api`

因此实际接口路径是：

### 认证

- `POST /api/auth/login`
- `POST /api/auth/logout`
- `POST /api/auth/token/refresh`

### 用户管理

- `POST /api/user/add`
- `GET /api/user/list`
- `POST /api/user/delete`
- `GET /api/user/login/info`

### 婚礼音乐

- `POST /api/wedding/music/add`
- `GET /api/wedding/music/list`

### 婚礼照片墙

- `GET /api/wedding/photo/wall/list`
- `GET /api/wedding/photo/wall/list/all`
- `POST /api/wedding/photo/wall/add`
- `POST /api/wedding/photo/wall/edit`
- `POST /api/wedding/photo/wall/delete`

### OSS / 图片

- `GET /api/oss/credentials`
- `GET /api/oss/images/list`
- `GET /api/image/asyncOss`
- `GET /api/image/task_status/<task_id>`
- `POST /api/upload/images`

### 体重管理

- `POST /api/weight/record/add`
- `POST /api/weight/record/edit`
- `POST /api/weight/record/delete`
- `GET /api/weight/records`
- `GET /api/weight/records/all`
- `GET /api/weight/record/latest`
- `GET /api/weight/summary`

### 餐馆菜品

- `GET /api/chuan-dai/dish/list`
- `GET /api/chuan-dai/dish/<dish_id>`
- `POST /api/chuan-dai/dish`
- `PUT /api/chuan-dai/dish/<dish_id>`
- `DELETE /api/chuan-dai/dish/<dish_id>`
- `POST /api/chuan-dai/dish/<dish_id>/toggle`

### 测试 / 通用

- `GET /api/common/logger`
- `GET /api/common/index`
- `GET /api/test/db`
- `GET /api/test/flask_env`
- `GET /api/test/celery`
- `GET /health`

## 主要模块

### `api/auth_api.py`

负责登录、登出和刷新令牌。登录成功后同时返回 access token、refresh token，并写入 Cookie。当前登录验证使用 `bcrypt.checkpw`。

### `api/user_api.py`

负责后台用户增删查和当前登录用户信息。新增用户时使用 Werkzeug 的 `generate_password_hash(password, method='pbkdf2:sha256')`。

### `api/wedding_api.py`

负责婚礼照片墙和音乐管理。照片墙使用 `WeddingPhotoWall` 模型，删除照片时会同步删除 OSS 对象。

### `api/oss_api.py`

负责生成 OSS 表单直传凭证，以及读取已同步到数据库的图片列表。`type=music` 时目录为 `wedding/music/`，`type=image` 时目录为 `wedding/image/`。

### `api/image_api.py`

负责从 OSS 的 `images/` 前缀异步扫描图片并写入 `image` 表。`/image/asyncOss` 会派发 Celery 任务，`/image/task_status/<task_id>` 查询任务状态。

### `api/dish_api.py`

餐馆菜品 CRUD。该模块绕过 Flask-SQLAlchemy 默认 session，直接用 `DATABASE_URL_RESTAURANT` 创建 SQLAlchemy engine 和 session。

### `api/weight_api.py`

体重记录 CRUD 和汇总接口。接口需要登录，使用 JWT identity 作为 `user_identity` 保存个人记录，默认走综合后台数据库。

## 数据模型

| 模型 | 表名 | 作用 |
| --- | --- | --- |
| `User` | `app_user` | 后台用户，含 `uid`、用户名、密码、角色 |
| `WeddingPhotoWall` | `wedding_photo_wall` | 婚礼照片墙 |
| `WeddingMusic` | `wedding_music` | 婚礼音乐 |
| `Image` | `image` | OSS 图片元信息 |
| `Dish` | `Dish` | 餐馆菜品，使用餐馆数据库 |
| `WeightRecord` | `weight_record` | 体重记录，使用综合后台数据库 |

## 多数据库设计

`config.py` 定义两个数据库地址：

- `DATABASE_URL`：综合后台默认数据库，用于用户、婚礼、图片等。
- `DATABASE_URL_RESTAURANT`：餐馆系统数据库，用于 `/api/chuan-dai/*` 菜品接口。

当前实际使用方式：

- Flask-SQLAlchemy 默认绑定 `DATABASE_URL`。
- `api/dish_api.py` 直接创建独立 engine 绑定 `DATABASE_URL_RESTAURANT`。
- `utils/db_router.py` 提供了按 URL 选择数据库的工具，但目前主路径未使用。

## 异步任务

`mycelery.py` 注册两个任务：

- `test_celery_task`
- `fetch_images_from_oss`

Celery broker 和 result backend 都使用 `REDIS_URL`。任务运行时通过自定义 `ContextTask` 包裹 Flask app context，因此任务里可以访问数据库和 Flask 配置。

## 部署

`Dockerfile` 使用 `python:3.11-slim`，安装依赖后以非 root 用户运行 Gunicorn。

`deployment.yaml` 包含：

- Deployment：默认 2 副本，容器端口 5000
- Service：ClusterIP，80 转 5000
- Ingress：域名 `api.tt829.cn`
- 探针：`/health`
- Secret：`DATABASE_URL`、`DATABASE_URL_RESTAURANT`、`JWT_SECRET_KEY`

## 环境变量

关键环境变量见 `.env.example`：

- `DATABASE_URL`
- `DATABASE_URL_RESTAURANT`
- `JWT_SECRET_KEY`
- `REDIS_URL`
- `OSS_ACCESS_KEY_ID`
- `OSS_ACCESS_KEY_SECRET`
- `OSS_BUCKET_NAME`
- `FLASK_ENV`
- `GUNICORN_WORKERS`
- `GUNICORN_THREADS`
- `LOG_LEVEL`

## 响应约定

业务接口多数返回 HTTP 200，并通过 JSON 中的 `code` 表示业务状态：

```json
{
  "code": 200,
  "message": "Success",
  "data": {}
}
```

异常或业务错误多数也返回 HTTP 200，但 `code` 为 500、404、5001 等。这是现有前端可能依赖的约定，修改时要确认前端兼容性。

## 当前维护风险

1. `auth_api.py` 登录使用 `bcrypt.checkpw`，但 `user_api.py` 创建用户时使用 Werkzeug `pbkdf2:sha256`。这会导致新建用户可能无法通过登录校验。迁移密码算法前需要统一存量用户和新用户策略。
2. `upload_api.py` 创建 `Image(name=filename, path=filesave)`，但 `Image.__init__` 要求 `last_modified`、`size`、`content_type`，该接口当前会抛参数缺失错误。
3. `supabase/migrations/001_initial_tables.sql` 中照片墙排序列是 `order_num`，模型字段是 `order`。如果数据库按迁移脚本建表，模型查询/写入可能不匹配。
4. `wedding_api.py` 中 `@route('/wedding/music/add', methods=['Post'])` 大小写不统一，Flask 通常会规范化方法，但建议改为 `POST` 保持一致。
5. 多个需要管理权限的接口没有 `@jwt_required()`，例如婚礼照片墙增删改、音乐增删查、餐馆菜品接口。是否需要公开访问要结合前端和业务确认。
6. `utils/db_utils.py` 通过模型文件名推断表名，例如 `wedding_photo_wall.py`，但 `Dish` 表名是大写 `Dish`，`User` 表名是 `app_user`。缺表判断和真实表名并不完全一致。
7. `utils/oss_utils.py` 只是一个很薄的 OSSClient 包装，导入了一些未使用依赖，可后续整理。
8. `config.py` 在未配置 `DATABASE_URL_RESTAURANT` 时仍会让 `dish_api.py` 创建空连接字符串 engine，启动或导入时可能失败。
9. JWT Cookie 在配置中 `JWT_COOKIE_SECURE = False`，生产环境如果通过 HTTPS 使用 Cookie，建议按环境切换为 `True` 并评估 SameSite / CSRF 设置。
10. 项目没有 `tests/` 目录，当前无法运行有效测试套件；`api/test_api.py` 是业务测试接口，不是 pytest 测试。

## 后续建议

优先级较高：

- 统一用户密码哈希算法，保证新增用户可登录。
- 修复 `upload_api.py` 与 `Image.__init__` 的参数不一致。
- 校准迁移脚本和 SQLAlchemy 模型，尤其是 `wedding_photo_wall.order` / `order_num`。
- 明确哪些接口需要 JWT，并补齐鉴权。
- 为 auth、user、wedding photo wall、dish API 增加基础 pytest 测试。

优先级中等：

- 将 `dish_api.py` 的 session 管理改成 `try/finally` 或上下文管理，避免异常分支 session 未关闭。
- 将 `create_missing_tables` 从生产启动链路中移出，改由明确的迁移流程管理表结构。
- 整理响应状态码策略，逐步区分 HTTP 状态和业务 `code`。
- 清理未使用的导入与工具函数，降低维护成本。
