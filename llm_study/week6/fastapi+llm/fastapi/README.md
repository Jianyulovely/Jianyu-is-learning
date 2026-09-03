# FastAPI 学习教程项目

这是一个完整的 FastAPI 学习项目，按照教程的8个章节组织，从基础语法到完整的项目实战。

## 项目结构

```
fastapi/
├── requirements.txt                 # 项目依赖
├── README.md                       # 项目说明
├── chapter1_basics/                # 第1章：环境安装与配置
│   └── main.py                     # 基础 FastAPI 应用
├── chapter2_syntax/                # 第2章：FastAPI 基础语法
│   └── main.py                     # 路由、参数、请求体演示
├── chapter3_models/                # 第3章：数据模型与验证
│   └── main.py                     # Pydantic 模型和验证
├── chapter4_async_middleware/      # 第4章：异步处理与中间件
│   └── main.py                     # 异步处理和中间件演示

```

## 环境安装

### 1. 创建虚拟环境
```bash
# 使用 venv 创建虚拟环境
python -m venv fastapi_env

# 激活虚拟环境
# Windows:
fastapi_env\Scripts\activate
# macOS/Linux:
source fastapi_env/bin/activate
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

## 运行项目

### 方法一：直接运行各章节
```bash
# 第1章：基础应用
python -m uvicorn chapter1_basics.main:app --reload --port 8001

# 第2章：基础语法
python -m uvicorn chapter2_syntax.main:app --reload --port 8002

# 第3章：数据模型与验证
python -m uvicorn chapter3_models.main:app --reload --port 8003

# 第4章：异步处理与中间件
python -m uvicorn chapter4_async_middleware.main:app --reload --port 8004


```

### 方法二：直接运行 Python 文件
```bash
# 进入对应章节目录
cd chapter1_basics
python main.py

# 或者
cd chapter2_syntax
python main.py
```

## 各章节学习内容

### 第1章：环境安装与配置
- **文件**: `chapter1_basics/main.py`
- **内容**: 
  - FastAPI 应用创建
  - 基础路由定义
  - 服务器启动配置
- **学习要点**: 
  - 了解 FastAPI 项目结构
  - 学会创建最简单的 API
  - 理解 uvicorn 服务器的使用

### 第2章：FastAPI 基础语法
- **文件**: `chapter2_syntax/main.py`
- **内容**:
  - 路径参数和查询参数
  - 请求体处理
  - 不同 HTTP 方法
  - 枚举类型参数
  - 响应模型
- **学习要点**:
  - 掌握 FastAPI 的路由定义
  - 理解参数类型自动转换
  - 学会使用 Pydantic 模型

### 第3章：数据模型与验证
- **文件**: `chapter3_models/main.py`
- **内容**:
  - Pydantic 模型定义
  - 字段验证和约束
  - 自定义验证器
  - 嵌套模型
  - 响应模型过滤
- **学习要点**:
  - 深入理解 Pydantic 数据验证
  - 学会编写复杂的数据模型
  - 掌握数据校验和错误处理

### 第4章：异步处理与中间件支持
- **文件**: `chapter4_async_middleware/main.py`
- **内容**:
  - 异步 vs 同步路由
  - 中间件编写和使用
  - 并发处理演示
  - WebSocket 支持
  - 性能测试
- **学习要点**:
  - 理解异步编程的优势
  - 学会编写和使用中间件
  - 掌握并发处理技巧


每个章节都建立在前面章节的基础上，建议按顺序学习。

## 技术栈

- **Web框架**: FastAPI
- **ASGI服务器**: Uvicorn
- **数据验证**: Pydantic
- **数据库**: SQLite (演示) / PostgreSQL (生产推荐)
- **ORM**: SQLAlchemy
- **认证**: JWT + OAuth2
- **异步支持**: asyncio
- **文档**: 自动生成 OpenAPI 文档

## 参考资源

- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [Pydantic 文档](https://docs.pydantic.dev/)
- [Python asyncio 文档](https://docs.python.org/3/library/asyncio.html) 