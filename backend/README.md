# MedLens Backend

MedLens 后端服务，基于 FastAPI 实现的 GraphRAG 架构用药安全风险核查系统。

## 快速开始

### 1. 激活 Conda 环境

```bash
conda activate medlens-graphrag
```

### 2. 配置环境变量

```bash
cd backend
cp .env.example .env
```

编辑 `.env` 文件，填入你的 API Key：

```env
# 百度 OCR API（必需）
BAIDU_OCR_API_KEY=你的百度云 API Key
BAIDU_OCR_SECRET_KEY=你的百度云 Secret Key

# DeepSeek API（必需）
DEEPSEEK_API_KEY=你的 DeepSeek API Key

# Embedding 模型（可选）
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

### 3. 启动服务

```bash
uvicorn app.main:app --reload --port 8000
```

启动成功后：
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

## API 端点

### 健康检查

```bash
GET /health
```

响应示例：
```json
{
  "status": "ok",
  "message": "MedLens API is running",
  "timestamp": "2024-01-01T00:00:00"
}
```

### 索引状态

```bash
GET /api/index/status
```

返回 GraphRAG 索引的构建状态，包括：
- artifacts 数量（documents, text_units, entities, relationships, communities, community_reports）
- vector_store 状态（text_units, entities, community_reports）

### 构建索引

```bash
POST /api/index/build
```

触发 GraphRAG 索引构建流程：
1. 加载种子文档
2. 文本分块（TextUnits）
3. 实体和关系抽取
4. 社区检测
5. 社区报告生成
6. 向量索引构建

### 扫描药品

```bash
POST /api/scan
Content-Type: multipart/form-data

Parameters:
- file: 图片文件
- age: 用户年龄
- gender: 用户性别
- pregnancy_status: 怀孕/哺乳状态
- chronic_diseases: 慢性疾病（JSON 数组）
- drinking_habit: 饮酒习惯（布尔值）
- coffee_habit: 咖啡习惯（布尔值）
- grapefruit_habit: 西柚习惯（布尔值）
```

响应示例：
```json
{
  "ocr": {
    "source": "baidu_ocr",
    "need_manual_input": false,
    "ocr_text": "药品说明书内容..."
  },
  "extraction": {
    "summary": "抽取结果摘要",
    "need_user_confirm": false,
    "items": [...]
  },
  "graphrag": {
    "entity_link": {...},
    "graph_context": {...},
    "text_context": {...},
    "community_context": {...},
    "risk_cards": [...],
    "overall_summary": "总体风险评估"
  }
}
```

## 项目结构

```
backend/
├── app/                    # 应用代码
│   ├── main.py            # FastAPI 入口
│   ├── config.py          # 配置管理
│   ├── logger.py          # 日志工具
│   ├── exceptions.py      # 异常处理
│   ├── safety.py          # 安全工具
│   ├── schemas.py         # Pydantic 模型
│   ├── services/          # 业务服务
│   │   ├── baidu_ocr_service.py       # 百度 OCR 服务
│   │   ├── deepseek_service.py        # DeepSeek LLM 服务
│   │   ├── embedding_service.py       # Embedding 服务
│   │   ├── graphrag_service.py        # GraphRAG 核心服务
│   │   ├── index_pipeline_service.py  # 索引构建流程
│   │   ├── query_pipeline_service.py  # 查询流程
│   │   ├── community_service.py       # 社区检测服务
│   │   ├── report_generate_service.py # 报告生成服务
│   │   └── query_entity_extract_service.py # 查询实体抽取
│   ├── data/              # 数据目录
│   │   └── seed_documents/  # 种子文档
│   ├── storage/           # 存储目录
│   │   ├── artifacts/     # 中间产物
│   │   │   ├── documents/
│   │   │   ├── text_units/
│   │   │   ├── entities/
│   │   │   ├── relationships/
│   │   │   ├── communities/
│   │   │   └── community_reports/
│   │   └── vectors/       # 向量索引
│   │       ├── text_units/
│   │       ├── entities/
│   │       └── community_reports/
│   └── uploads/           # 上传文件
├── .env.example           # 环境变量示例
├── .env                   # 环境变量（需自行创建）
└── README.md              # 本文档
```

## 核心服务说明

### 1. 百度 OCR 服务

**文件**：`app/services/baidu_ocr_service.py`

**功能**：
- 调用百度智能云 OCR API
- 识别药品图片中的文字
- 返回结构化 OCR 结果

**错误码**：
- `BAIDU_OCR_CONFIG_MISSING`：未配置 API Key

### 2. DeepSeek 服务

**文件**：`app/services/deepseek_service.py`

**功能**：
- 实体抽取（从 OCR 文本中提取药品实体）
- 社区报告生成（汇总社区知识）
- 风险推理（识别用药风险）

**错误码**：
- `DEEPSEEK_CONFIG_MISSING`：未配置 API Key
- `DEEPSEEK_JSON_PARSE_FAILED`：JSON 解析失败

### 3. Embedding 服务

**文件**：`app/services/embedding_service.py`

**功能**：
- 加载 sentence-transformers 模型
- 生成文本向量
- 支持多语言（中文/英文）

**错误码**：
- `EMBEDDING_MODEL_LOAD_FAILED`：模型加载失败

### 4. GraphRAG 服务

**文件**：`app/services/graphrag_service.py`

**功能**：
- 索引状态检查
- 图谱查询
- 实体链接
- 局部搜索

**错误码**：
- `INDEX_NOT_READY`：索引未就绪

### 5. 索引构建服务

**文件**：`app/services/index_pipeline_service.py`

**流程**：
1. 加载种子文档
2. 文本分块（TextUnits）
3. 使用 DeepSeek 抽取实体和关系
4. 构建 NetworkX 图
5. Louvain 社区检测
6. 生成社区报告
7. 构建 LanceDB 向量索引

**错误码**：
- `INDEX_BUILD_FAILED`：索引构建失败

### 6. 查询服务

**文件**：`app/services/query_pipeline_service.py`

**流程**：
1. OCR 识别药品图片
2. DeepSeek 抽取药品实体
3. 实体链接到知识图谱
4. 图谱局部搜索（多跳推理）
5. 文本单元检索
6. 社区报告检索
7. 风险推理和报告生成

## 日志说明

### 日志级别

- `INFO`：关键流程节点
- `DEBUG`：详细调试信息
- `ERROR`：错误信息
- `WARNING`：警告信息

### 成功日志示例

```
[Startup] MedLens API started
[Index] stage=load_documents, count=10
[Index] stage=extract_entities, progress=50%
[Index] stage=community_detection, communities=5
[Index] stage=generate_reports, completed
[Index] stage=build_vectors, completed
[Index] build completed
[OCR] success, text_length=1234
[QueryExtract] DeepSeek extraction success, entities=15
[LocalSearch] completed, paths=3, relationships=12
[Report] DeepSeek report generated, risks=2
```

### 错误日志示例

```
[ERROR] stage=build_index, code=DEEPSEEK_CONFIG_MISSING, message=DeepSeek API Key 未配置
[ERROR] stage=ocr, code=BAIDU_OCR_CONFIG_MISSING, message=百度 OCR API Key 未配置
[ERROR] stage=embedding, code=EMBEDDING_MODEL_LOAD_FAILED, message=模型加载失败
[ERROR] stage=scan, code=INDEX_NOT_READY, message=索引未就绪
```

## 常见错误及解决方法

### 1. BAIDU_OCR_CONFIG_MISSING

**错误信息**：百度 OCR API Key 未配置

**原因**：
- `.env` 文件不存在
- `BAIDU_OCR_API_KEY` 或 `BAIDU_OCR_SECRET_KEY` 未配置

**解决方法**：
```bash
# 1. 检查 .env 文件是否存在
ls -la .env

# 2. 检查配置是否正确
cat .env | grep BAIDU

# 3. 配置后重启服务
uvicorn app.main:app --reload --port 8000
```

### 2. DEEPSEEK_CONFIG_MISSING

**错误信息**：DeepSeek API Key 未配置

**原因**：
- `.env` 文件不存在
- `DEEPSEEK_API_KEY` 未配置

**解决方法**：
```bash
# 1. 检查配置
cat .env | grep DEEPSEEK

# 2. 配置后重启服务
```

### 3. EMBEDDING_MODEL_LOAD_FAILED

**错误信息**：Embedding 模型加载失败

**原因**：
- 网络连接问题
- 磁盘空间不足
- 模型文件损坏

**解决方法**：
```bash
# 1. 检查网络连接
ping huggingface.co

# 2. 检查磁盘空间
df -h

# 3. 手动下载模型
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')"

# 4. 重启服务
```

### 4. VECTOR_TABLE_NOT_FOUND

**错误信息**：向量表不存在

**原因**：
- 索引未构建
- 存储目录被删除

**解决方法**：
```bash
# 1. 调用 /api/build-index 构建索引
curl -X POST http://localhost:8000/api/build-index

# 2. 检查存储目录
ls -la storage/vectors/

# 3. 重启服务
```

### 5. INDEX_NOT_READY

**错误信息**：索引未就绪

**原因**：
- 索引正在构建中
- 索引构建失败

**解决方法**：
```bash
# 1. 检查索引状态
curl http://localhost:8000/api/index-status

# 2. 等待构建完成或重新构建
curl -X POST http://localhost:8000/api/build-index
```

## 数据流

### 索引构建流程

```
种子文档 → 文本分块 → 实体抽取 → 关系抽取
    ↓
构建图谱 → 社区检测 → 报告生成 → 向量索引
```

### 查询流程

```
上传图片 → OCR 识别 → 实体抽取 → 实体链接
    ↓
风险报告 ← 报告生成 ← 局部搜索 ← 图谱查询
```

## 配置说明

### 环境变量

| 变量名 | 必需 | 说明 | 默认值 |
|--------|------|------|--------|
| `BAIDU_OCR_API_KEY` | ✅ | 百度 OCR API Key | - |
| `BAIDU_OCR_SECRET_KEY` | ✅ | 百度 OCR Secret Key | - |
| `DEEPSEEK_API_KEY` | ✅ | DeepSeek API Key | - |
| `EMBEDDING_MODEL` | ❌ | Embedding 模型名称 | sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 |
| `LOG_LEVEL` | ❌ | 日志级别 | INFO |

### 存储目录

- `storage/artifacts/`：GraphRAG 中间产物
- `storage/vectors/`：LanceDB 向量索引
- `uploads/`：用户上传的临时文件

## 性能优化建议

### 1. 缓存

- 实体抽取结果可缓存
- Embedding 向量可预计算

### 2. 批量处理

- 批量生成 Embedding
- 批量调用 DeepSeek API

### 3. 数据库

- 生产环境建议使用 PostgreSQL 存储元数据
- 使用 Redis 缓存热点数据

### 4. 图数据库

- 当前使用 NetworkX（内存）
- 生产环境建议使用 Neo4j

## 开发指南

### 添加新的服务

1. 在 `app/services/` 创建新服务文件
2. 实现服务类
3. 在 `main.py` 中注册
4. 添加单元测试

### 添加新的 API 端点

1. 在 `main.py` 添加路由
2. 定义请求/响应模型（`schemas.py`）
3. 实现业务逻辑
4. 添加错误处理
5. 更新 API 文档

### 调试技巧

```bash
# 1. 启用 DEBUG 日志
export LOG_LEVEL=DEBUG
uvicorn app.main:app --reload --port 8000

# 2. 查看实时日志
tail -f logs/app.log

# 3. 使用 Python debugger
import pdb; pdb.set_trace()
```

## 测试

### 健康检查

```bash
curl http://localhost:8000/health
```

### 检查索引状态

```bash
curl http://localhost:8000/api/index-status
```

### 构建索引

```bash
curl -X POST http://localhost:8000/api/build-index
```

### 扫描药品

```bash
curl -X POST http://localhost:8000/api/scan \
  -F "file=@medicine.jpg" \
  -F "age=68" \
  -F "gender=male" \
  -F "chronic_diseases=[\"高血压\"]"
```

## 部署建议

### 生产环境

1. 使用 Gunicorn 代替 uvicorn
2. 配置 Nginx 反向代理
3. 启用 HTTPS
4. 配置日志轮转
5. 监控服务状态

### Docker 部署

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt

CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
```

## 许可证

MIT License

---

**MedLens Backend - 基于 GraphRAG 的用药安全风险核查系统**
