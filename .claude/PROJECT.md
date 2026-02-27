# server-console - Claude AI 配置

## 项目概述

**婚礼服务后台管理系统** - 为婚礼场景提供照片墙、音乐管理等功能的管理后台。

## 技术栈

| 分类 | 技术 |
|------|------|
| 框架 | Flask |
| 数据库 | PostgreSQL (Supabase) |
| ORM | SQLAlchemy |
| 认证 | Flask-JWT-Extended (Cookie-based) |
| 存储 | 阿里云 OSS |
| 异步任务 | Celery + Redis |
| 部署 | Docker + K8s |

## 项目结构

```
server-console/
├── api/                    # API 路由
│   ├── auth_api.py         # 登录/登出/刷新令牌
│   ├── user_api.py         # 用户管理
│   ├── wedding_api.py      # 婚礼照片墙、音乐管理
│   ├── image_api.py        # 图片同步 (OSS + Celery)
│   ├── oss_api.py          # OSS 直接上传
│   ├── upload_api.py       # 上传接口
│   └── test_api.py         # 测试接口
├── model/                  # 数据模型
│   ├── user.py             # 用户表 (app_user)
│   ├── wedding_photo_wall.py  # 婚礼照片墙
│   ├── wedding_music.py     # 婚礼音乐
│   └── image.py            # 图片记录
├── utils/                  # 工具函数
│   ├── db_utils.py         # 数据库初始化
│   ├── jwt_errors.py       # JWT 错误处理
│   ├── oss_utils.py        # OSS 客户端
│   └── register_api_blueprints.py  # 蓝图注册
├── supabase/               # Supabase 迁移脚本
├── templates/              # Flask 模板
├── static/                 # 静态文件
├── app.py                 # 应用入口
├── config.py              # 配置 (数据库、JWT、OSS)
├── mycelery.py            # Celery 配置
└── deployment.yaml        # K8s 部署配置

## 核心功能

### 1. 认证模块 (auth_api)
- `POST /login` - 用户登录 (用户名/密码)
- `POST /logout` - 退出登录
- `POST /token/refresh` - 刷新令牌

### 2. 婚礼照片墙 (wedding_api)
- `POST /wedding/photo/wall/add` - 添加照片
- `POST /wedding/photo/wall/edit` - 编辑照片
- `POST /wedding/photo/wall/delete` - 删除照片
- `GET /wedding/photo/wall/list` - 分页列表
- `GET /wedding/photo/wall/list/all` - 全部列表

### 3. 婚礼音乐 (wedding_api)
- `POST /wedding/music/add` - 添加音乐
- `GET /wedding/music/list` - 音乐列表

### 4. 图片管理 (image_api)
- `POST /image/asyncOss` - 异步同步 OSS 图片到数据库
- `GET /image/task_status/<task_id>` - 检查同步任务状态

## 启动方式

```bash
# 本地开发
python app.py

# Docker
docker build -t server-console .
docker run -p 5000:5000 server-console

# K8s
kubectl apply -f deployment.yaml
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| DATABASE_URL | Supabase 数据库连接字符串 | postgresql://postgres:password@localhost:5432/postgres |
| JWT_SECRET_KEY | JWT 密钥 | change-this-to-a-strong-secret-key |
| REDIS_URL | Redis 连接字符串 | redis://localhost:6379/0 |
| OSS_ACCESS_KEY_ID | 阿里云 OSS AccessKey | - |
| OSS_ACCESS_KEY_SECRET | 阿里云 OSS Secret | - |
| OSS_BUCKET_NAME | OSS Bucket 名称 | ray321 |
| FLASK_ENV | 生产环境标识 | - |

## API 响应格式

```json
{
  "code": 200,
  "message": "Success",
  "data": { ... }
}
```

## 数据库表

| 表名 | 说明 |
|------|------|
| app_user | 用户表 |
| wedding_photo_wall | 婚礼照片墙 |
| wedding_music | 婚礼音乐 |
| image | 图片记录 |

## 开发注意事项

1. JWT 使用 Cookie 存储，需配置 `JWT_TOKEN_LOCATION = ["cookies"]`
2. OSS 使用阿里云成都节点
3. 生产环境使用内网 endpoint
4. 异步任务通过 Celery 执行
5. 用户角色: super_admin, admin, user
