# AGENTS.md - ashare-platform 开发指南

A股数据采集与平台服务项目开发指南。

## 项目结构

```
ashare-platform/
├── ashare_data/          # 数据采集基础设施
│   ├── core/             # 核心工具（config, http_client, cache, scraper）
│   ├── fetchers/         # 数据源采集模块（market_sentiment, trend_scanner, ...）
│   ├── cdp/              # Chrome DevTools Protocol 客户端
│   └── *.py              # CLI 入口模块
├── app/                  # FastAPI 后端服务
│   ├── app/
│   │   ├── api/routes/   # REST API 路由（emotion, market_reviews, ...）
│   │   ├── core/         # 配置和运行时设置
│   │   ├── db/           # 数据库会话管理
│   │   ├── models/       # SQLAlchemy ORM 模型
│   │   ├── pipelines/    # 数据处理流水线（build_emotion_facts, ...）
│   │   ├── repositories/ # 数据访问层
│   │   ├── services/     # 业务逻辑服务
│   │   └── tasks/        # 定时任务
│   ├── alembic/          # 数据库迁移脚本
│   └── tests/            # 后端 API 测试
├── tests/                # ashare_data 单元测试
├── docker/               # Docker 部署配置
└── data/                 # 数据存储（ephemeral/ + retained/）
```

**边界划分**：
- `ashare_data/` - 数据采集、清洗、基础计算能力
- `app/` - 数据持久化、API 服务、定时调度

## IRON RULES

- **NO RAW SQL IN ROUTES**: 所有数据库操作通过 repositories 层
- **NO BUSINESS LOGIC IN FETCHERS**: fetchers 只负责原始数据获取
- **NO CROSS-IMPORT**: ashare_data 不依赖 app，app 可依赖 ashare_data
- **NO DEPLOY WITHOUT TEST**: 核心逻辑变更必须附带测试

## 开发环境

### 1. 安装依赖

```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate

# 安装项目
pip install -e .

# 安装开发依赖
pip install pytest pytest-asyncio
```

### 2. 初始化数据库

```bash
# 创建数据库表
ashare-platform init-db

# 或使用 alembic
alembic upgrade head
```

### 3. 启动服务

```bash
# 开发模式（热重载）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 或 Docker
cd docker && docker compose up -d
```

## 构建与测试

```bash
# 单元测试 - ashare_data
python -m unittest discover -s tests -p "test_*.py"

# 单元测试 - app
python -m pytest app/tests/ -v

# 语法检查
python -m py_compile <file.py>

# 类型检查（可选）
mypy ashare_data/ app/app/
```

## 代码风格

### 1. 导入排序

```python
# 标准库
import json
import logging
from datetime import datetime
from typing import Any

# 第三方
import sqlalchemy
from fastapi import APIRouter

# 本地模块
from app.db.session import open_session
from ashare_data.core.config import DATA_DIR
```

### 2. 类型注解

```python
# Python 3.10+ 风格
def fetch_data(date_str: str | None = None) -> list[dict[str, Any]]:
    ...

# 复杂类型用别名
EmotionRow = dict[str, Any]
EmotionRows = list[EmotionRow]
```

### 3. 错误处理

```python
def fetch_data(url: str) -> list[dict]:
    try:
        return _fetch_internal(url)
    except Exception as e:
        logger.exception("fetch_data 失败: %s", e)
        return []  # 永不抛出，返回空集合
```

### 4. Docstring（Google 风格）

```python
def build_emotion_facts(trade_date: str) -> dict[str, Any]:
    """构建每日市场情绪事实。

    Args:
        trade_date: 交易日期，格式 YYYY-MM-DD

    Returns:
        情绪指标字典，包含涨停数、跌停数、封板率等

    Raises:
        ValueError: 日期格式错误
    """
```

## 数据库规范

### 模型定义

```python
# app/models/market_emotion_daily.py
from app.models.base import Base
from sqlalchemy import String, Float, Date, JSON
from sqlalchemy.orm import Mapped, mapped_column

class MarketEmotionDaily(Base):
    __tablename__ = "market_emotion_daily"
    
    trade_date: Mapped[str] = mapped_column(Date, primary_key=True)
    limit_up_count: Mapped[int]
    evidence_json: Mapped[dict] = mapped_column(JSON)
```

### 迁移流程

```bash
# 创建迁移
alembic revision --autogenerate -m "add new table"

# 执行迁移
alembic upgrade head

# 回滚
alembic downgrade -1
```

## API 设计

### 路由结构

```python
# app/api/routes/emotion.py
from fastapi import APIRouter

router = APIRouter(tags=["emotion"])

@router.get("/market-emotion/daily/{trade_date}")
def get_market_emotion(trade_date: str) -> MarketEmotionResponse:
    """获取单日市场情绪。"""
    ...
```

### 响应模型

```python
# app/schemas/api.py
from pydantic import BaseModel

class MarketEmotionDailyResponse(BaseModel):
    trade_date: str
    limit_up_count: int
    # ... 其他字段
```

## Docker 部署

### 本地开发

```bash
cd docker
docker compose up -d --build
docker compose logs -f
```

### 生产部署

```bash
# 构建镜像
docker build -f app/Dockerfile -t ashare-platform:latest .

# 运行容器
docker run -d \
  --name ashare_platform \
  -p 8000:8000 \
  -v $(pwd)/data:/data \
  -e ASHARE_PLATFORM_HOME=/data \
  ashare-platform:latest
```

## 数据源开发

### 已有 Fetcher 列表

| 模块 | 数据源 | 用途 |
|------|--------|------|
| `new_high` | 同花顺数据中心 | 历史新高股票 |
| `market_sentiment` | 东方财富 | 市场情绪指标 |
| `trend_scanner` | 多源整合 | 趋势扫描 |
| `consecutive_red` | 东财热度榜 | 连续 N 日收阳股票 |
| `broker_account` | 龙虎榜数据 | 机构席位交易 |
| `eastmoney_guba` | 东财股吧 | 个股讨论热度 |
| `taoguba` | 淘股吧 | 论坛精华帖 |

### 添加新 fetcher

1. 在 `ashare_data/fetchers/` 创建模块
2. 实现 `fetch_*` 函数，返回标准格式
3. 添加单元测试
4. 更新 AGENTS.md 数据源列表

### Fetcher 模板

```python
"""XXX 数据源采集。

Purpose: 采集 XXX 数据
DataSource: XXX 网站
"""

import logging
from typing import Any

from ashare_data.core.http_client import http_json

logger = logging.getLogger(__name__)
BASE_URL = "https://api.xxx.com"


def fetch_xxx_data(date_str: str | None = None) -> list[dict[str, Any]]:
    """获取 XXX 数据。
    
    Args:
        date_str: 日期，格式 YYYY-MM-DD，默认今日
        
    Returns:
        数据列表，出错时返回空列表
    """
    try:
        url = f"{BASE_URL}/endpoint"
        resp = http_json(url, timeout=15)
        return _parse_response(resp)
    except Exception as e:
        logger.exception("fetch_xxx_data 失败: %s", e)
        return []


def _parse_response(resp: dict) -> list[dict]:
    """解析响应数据。"""
    return resp.get("data", [])
```

## 完成标准

提交前必须全部通过：

- [ ] 相关测试通过（unittest 或 pytest）
- [ ] 无语法错误（py_compile）
- [ ] 类型注解完整（Python 3.10+ 风格）
- [ ] Docstring 完整
- [ ] 无硬编码敏感信息
- [ ] 数据库迁移文件已生成（如有模型变更）

## PR 期望

- **标题**: `feat:` / `fix:` / `docs:` / `refactor:` 前缀
- **范围**: 一个 PR 对应一个连贯的工作单元
- **测试**: 新功能附带测试，Bug 修复附带复现用例
- **描述**: 说明变更内容、影响范围、测试方法
- **禁止**: 不得包含调试代码、注释掉的代码块、TODO 遗留

## 规范参考

- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 文档](https://docs.sqlalchemy.org/en/20/)
- [Alembic 文档](https://alembic.sqlalchemy.org/)
- [File Header Spec](https://github.com/agentskills/agentskills/blob/main/File-Header-Spec.md)

## 禁止事项

1. 禁止正则解析 HTML —— 使用 Scrapling Selector
2. 禁止硬编码敏感信息 —— 使用环境变量
3. 禁止在 fetchers 中直接操作数据库
4. 禁止循环导入 —— ashare_data 不能导入 app
5. 禁止在生产环境使用 `--reload`

## 数据目录

固定使用以下目录：

```python
# ashare_data/core/config.py
ASHARE_HOME = Path("~/.ashare-assistant").expanduser()
DATA_DIR = ASHARE_HOME / "data"
```

容器内通过 bind mount 映射：
- 宿主机: `~/Projects/ashare-data/data`
- 容器内: `/data`

## 联系方式

如有问题，参考原项目文档或提交 Issue。
