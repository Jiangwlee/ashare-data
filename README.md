# ashare-platform

A股数据采集与平台服务。本项目整合了数据采集基础设施（ashare-data）和 FastAPI 后端服务（ashare-platform），提供完整的数据采集、处理和 API 服务能力。

## 项目结构

```
ashare-platform/
├── ashare_data/          # 数据采集基础设施
│   ├── core/             # 核心工具（配置、HTTP客户端、缓存）
│   ├── fetchers/         # 数据源采集模块
│   ├── cdp/              # Chrome CDP 客户端
│   └── *.py              # CLI 模块（collect, diagnose, monitor等）
├── app/                  # FastAPI 后端服务
│   ├── app/              # 应用代码
│   │   ├── api/routes/   # API 路由
│   │   ├── core/         # 核心配置
│   │   ├── db/           # 数据库会话
│   │   ├── models/       # SQLAlchemy 模型
│   │   ├── pipelines/    # 数据处理流水线
│   │   ├── repositories/ # 数据仓库
│   │   ├── services/     # 业务服务
│   │   └── tasks/        # 定时任务
│   ├── alembic/          # 数据库迁移
│   ├── tests/            # 后端测试
│   └── Dockerfile        # 容器构建
├── tests/                # ashare_data 单元测试
├── docker/
│   ├── docker-compose.yml
│   └── .env              # 环境变量配置
├── data/                 # 数据存储目录（挂载到容器）
│   ├── ephemeral/        # 临时数据（原始采集数据）
│   └── retained/         # 持久化数据（SQLite数据库）
└── pyproject.toml        # 项目配置和依赖
```

## 快速开始

### 1. 安装依赖

```bash
# 进入项目目录
cd ~/Projects/ashare-data

# 安装到虚拟环境
pip install -e .
```

### 2. 启动服务（Docker）

```bash
cd docker
docker compose up -d

# 查看日志
docker compose logs -f

# 检查健康状态
curl http://127.0.0.1:8000/health
```

### 3. 本地开发运行

```bash
# 初始化数据库
ashare-platform init-db

# 运行服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API 端点

| 端点 | 描述 |
|------|------|
| `GET /health` | 健康检查 |
| `GET /market-emotion/daily/{trade_date}` | 获取单日市场情绪 |
| `GET /market-emotion/history?days=20` | 获取历史情绪数据 |
| `GET /theme-emotion/daily?trade_date=YYYY-MM-DD` | 获取板块情绪 |
| `GET /market-reviews/daily/{trade_date}` | 获取每日市场回顾 |
| `GET /trend-pool/daily/{trade_date}` | 获取趋势池 |
| `GET /theme-pool/daily/{trade_date}` | 获取板块池 |
| `GET /trade-dates` | 获取交易日历 |

## 数据采集

### 使用 Python API

```python
from ashare_data.fetchers.market_sentiment import fetch_market_sentiment_for_date
from ashare_data.fetchers.trend_scanner import fetch_ths_snapshot

# 获取市场情绪
sentiment = fetch_market_sentiment_for_date("2026-03-20")

# 获取趋势扫描数据
trends = fetch_ths_snapshot()
```

### 数据源列表

| 模块 | 数据源 | 说明 |
|------|--------|------|
| `fetchers/news.py` | 金融界 | 头条/每日/机会/实时/快讯 |
| `fetchers/funding.py` | 金融界 | 北向资金、主力净流入 |
| `fetchers/taoguba.py` | 淘股吧 | 热帖、推荐、热议 |
| `fetchers/trend_scanner.py` | JRJ/THS | 趋势评分、K线数据 |
| `fetchers/market_sentiment.py` | 同花顺 | 涨跌停计数、封板率 |
| `fetchers/market_breadth.py` | 搜狐/同花顺 | 涨跌平家数 |
| `fetchers/broker_account.py` | JVQuant | 账户持仓、委托记录 |

## 数据存储

### 目录结构

```
data/
├── ephemeral/           # 临时采集数据
│   └── YYYY-MM-DD/
│       └── raw/         # 原始JSON数据
└── retained/            # 持久化数据
    └── ashare_platform.db   # SQLite数据库
```

### 数据库模型

- `market_emotion_daily` - 每日市场情绪
- `market_review_daily` - 每日市场回顾
- `theme_pool_daily` - 每日板块池
- `trend_pool_daily` - 每日趋势池
- `theme_emotion_daily` - 板块情绪
- `theme_stock_daily` - 板块成分股
- `runs` - 任务执行记录

## Chrome CDP

用于处理需要真实浏览器上下文的数据源：

```python
from ashare_data.cdp.client import CDPClient

async with CDPClient() as client:
    page = await client.get_page("https://q.10jqka.com.cn/")
    data = await page.fetch_json("/api.php?t=indexflash")
```

默认依赖本机 Chrome DevTools endpoint：`http://127.0.0.1:9222`

## 测试

```bash
# 运行所有测试
python -m unittest discover -s tests -p "test_*.py"

# 运行特定测试
python -m unittest tests.test_funding_fetcher

# 运行后端测试
python -m pytest app/tests/ -v

# 语法检查
python -m py_compile ashare_data/core/http_client.py
```

## 部署

### Docker 部署

```bash
cd docker
docker compose up -d --build
```

### 环境变量

创建 `docker/.env` 文件：

```env
# OpenAI 配置（用于语义增强）
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4
OPENAI_API_KEY=your-api-key

# 主题池配置
ASHARE_THEME_POOL_PROFILE=default
```

## 相关项目

- **oh-my-superpowers**: Openclaw Agent Skills 仓库（原项目）
  - 位置：`~/Projects/oh-my-superpowers`
  - 包含：agent-roundtable, github-researcher 等 skills

## 技术栈

- **Python**: 3.10+
- **Web框架**: FastAPI + Uvicorn
- **数据库**: SQLAlchemy + SQLite + Alembic
- **HTTP客户端**: Scrapling (基于 curl_cffi)
- **HTML解析**: Scrapling Selector (lxml后端)
- **容器**: Docker + Docker Compose
- **测试**: unittest + pytest

## 注意事项

1. 数据目录 `data/` 通过 bind mount 挂载到容器
2. 数据库文件 `ashare_platform.db` 由容器和宿主机共享
3. 定时任务通过容器内的调度器执行
4. 数据采集保持 `~/.ashare-assistant` 目录兼容

## License

MIT
