# MedLens：家庭药箱安全雷达

## 项目定位

**MedLens** 是一个面向家庭慢病、老人、多药同服场景的 **Microsoft GraphRAG 风格用药安全风险核查系统**。

系统通过 OCR 技术识别药品说明书/医嘱图片，结合知识图谱进行深度用药安全分析，帮助用户识别潜在的用药风险，包括药物相互作用、禁忌症、剂量问题等。

## 本项目不是

- ❌ **不是普通 OCR + LLM**：我们不只是识别文字然后问大模型
- ❌ **不是简单向量 RAG**：我们不只是把文本切成块做向量检索
- ❌ **不是图谱页面展示**：我们没有花哨的图谱可视化页面
- ❌ **不是 AI 医生**：我们不提供诊断，只做用药安全核查
- ❌ **不是处方推荐系统**：我们不推荐药物，只识别风险

## GraphRAG 对齐能力

本项目完整实现了 Microsoft GraphRAG 的核心能力：

| 组件 | 说明 |
|------|------|
| **Documents** | 原始文档（药品图片 OCR 结果） |
| **TextUnits** | 文本单元，从文档中提取的语义片段 |
| **Entities** | 实体（药品、成分、疾病、症状等） |
| **Relationships** | 实体间关系（药物相互作用、适应症、禁忌症等） |
| **Communities** | 社区，基于图结构的实体分组（Louvain 算法） |
| **CommunityReports** | 社区报告，汇总社区内的知识（由 DeepSeek 生成） |
| **Vector Index** | TextUnit / Entity / CommunityReport 向量索引（LanceDB） |
| **Entity Linking** | 实体链接，将查询术语链接到图谱实体 |
| **Local Search** | 局部搜索，基于图的检索（多跳推理） |
| **Grounded Generation** | 基于检索结果的生成（风险报告） |

## 手动准备

在开始之前，你需要准备以下资源：

### 必需项

- ✅ **Conda**：用于管理 Python 环境
- ✅ **Node.js 18+**：用于构建前端
- ✅ **百度云 OCR API Key 和 Secret Key**：用于药品图片文字识别
- ✅ **DeepSeek API Key**：用于实体抽取、社区报告生成、风险推理
- ✅ **可联网环境**：首次启动需下载 sentence-transformers embedding 模型

### 获取 API Key 的步骤

#### 1. 百度智能云 OCR

1. 访问 [百度智能云](https://console.bce.baidu.com/)
2. 注册/登录账号
3. 进入「应用列表」→「文字识别」
4. 创建应用，选择「通用文字识别（标准版）」
5. 获取 API Key 和 Secret Key

#### 2. DeepSeek

1. 访问 [DeepSeek 开放平台](https://platform.deepseek.com/)
2. 注册/登录账号
3. 进入「API Keys」页面
4. 创建新的 API Key

## 创建环境

```bash
# 克隆项目
git clone <your-repo-url>
cd medlens-graphrag

# 创建 conda 环境
conda env create -f environment.yml
conda activate medlens-graphrag
```

## 配置后端环境变量

```bash
cd backend
cp .env.example .env
```

编辑 `.env` 文件，填入你的 API Key：

```env
# 百度 OCR API
BAIDU_OCR_API_KEY=你的百度云 API Key
BAIDU_OCR_SECRET_KEY=你的百度云 Secret Key

# DeepSeek API
DEEPSEEK_API_KEY=你的 DeepSeek API Key

# Embedding 模型（可选，默认使用 sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2）
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

**⚠️ 重要提示：**
- 不配置 API Key 会导致系统启动失败
- 请确保 API Key 有效且有足够额度
- 首次启动需联网下载 embedding 模型（约 500MB）

## 启动后端

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

启动成功后，访问 http://localhost:8000/docs 查看 API 文档。

## 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端默认运行在 http://localhost:5173

## 演示流程

### 1. 打开应用

访问 http://localhost:5173

### 2. 构建 GraphRAG Index

- 点击「构建 GraphRAG Index」按钮
- 等待构建完成（首次构建约需 2-5 分钟）
- 查看 Index Status Panel 显示构建结果

### 3. 填写用户画像

在 UserProfileForm 中填写：
- 年龄
- 性别
- 怀孕/哺乳状态
- 慢性疾病（多选）
- 饮酒、咖啡、西柚习惯

### 4. 上传药品图片

- 点击上传区域选择药品说明书/医嘱图片
- 支持 JPG、PNG 格式
- 点击「执行 OCR + DeepSeek + GraphRAG」

### 5. 查看结果

系统将展示：
- **OCR 结果**：识别出的文字
- **实体抽取**：从 OCR 文本中提取的药品实体
- **实体链接**：将实体链接到知识图谱
- **图谱检索**：相关的实体关系路径
- **文本检索**：相关的文本单元
- **社区报告**：相关社区的知识汇总
- **风险卡片**：识别出的用药风险（高/中/低）

## 日志说明

### 成功日志示例

```
[Index] build completed
[OCR] success
[QueryExtract] DeepSeek extraction success
[LocalSearch] completed
[Report] DeepSeek report generated
```

### 关键日志说明

| 日志 | 说明 |
|------|------|
| `[Index] build completed` | GraphRAG 索引构建完成 |
| `[OCR] success` | 百度 OCR 识别成功 |
| `[QueryExtract] DeepSeek extraction success` | DeepSeek 实体抽取成功 |
| `[LocalSearch] completed` | 图谱局部搜索完成 |
| `[Report] DeepSeek report generated` | 风险报告生成成功 |

## 常见错误

### 1. BAIDU_OCR_CONFIG_MISSING

**错误信息**：百度 OCR 配置缺失

**解决方法**：
1. 检查 `backend/.env` 文件是否存在
2. 确认 `BAIDU_OCR_API_KEY` 和 `BAIDU_OCR_SECRET_KEY` 已正确配置
3. 重启后端服务

### 2. DEEPSEEK_CONFIG_MISSING

**错误信息**：DeepSeek 配置缺失

**解决方法**：
1. 检查 `backend/.env` 文件是否存在
2. 确认 `DEEPSEEK_API_KEY` 已正确配置
3. 重启后端服务

### 3. EMBEDDING_MODEL_LOAD_FAILED

**错误信息**：Embedding 模型加载失败

**解决方法**：
1. 确保网络连接正常
2. 检查是否有足够磁盘空间
3. 尝试手动下载模型：
   ```python
   from sentence_transformers import SentenceTransformer
   model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
   ```
4. 重启后端服务

### 4. VECTOR_TABLE_NOT_FOUND

**错误信息**：向量表不存在

**解决方法**：
1. 先构建 GraphRAG Index
2. 检查 `backend/storage/vectors/` 目录是否存在
3. 重启后端服务

### 5. INDEX_NOT_READY

**错误信息**：索引尚未就绪

**解决方法**：
1. 等待 GraphRAG Index 构建完成
2. 查看 Index Status Panel 确认所有 artifacts 已构建
3. 确认 vector_store 中所有向量表已创建

## 医疗免责声明

⚠️ **重要声明**

**本系统仅供参考，不能替代专业医疗建议、诊断或治疗。**

### 使用限制

- ❌ 本系统不是医疗设备
- ❌ 本系统不提供诊断服务
- ❌ 本系统不推荐处方药物
- ❌ 本系统不能替代药师审核

### 使用条款

1. **仅供参考**：本系统提供的信息仅供科普和参考目的
2. **咨询专业人士**：用户在做出任何医疗决策前应咨询医生或药师
3. **责任免除**：开发者不对任何因使用本系统信息而导致的医疗后果承担责任
4. **信息准确性**：尽管我们努力确保信息准确，但不保证 100% 正确
5. **个体差异**：用药方案需考虑个体差异，请遵医嘱

### 紧急情况

如有紧急医疗情况，请立即：
- 📞 拨打急救电话（中国：120）
- 🏥 前往最近医院急诊科
- 👨‍⚕️ 咨询专业医疗人员

---

**开发者不对任何医疗后果承担责任。使用本系统即表示您已阅读并同意以上声明。**

## 当前未实现

以下功能在当前 MVP 版本中**尚未实现**：

- ❌ **真实权威药品库**：当前使用模拟数据，未接入国家药监局药品数据库
- ❌ **Neo4j**：当前使用 NetworkX 进行图计算，未使用专业图数据库
- ❌ **Fine-tune 模型**：当前使用通用 DeepSeek 模型，未针对医疗领域微调
- ❌ **药师审核**：当前无真人药师审核环节
- ❌ **登录和历史记录**：当前无用户系统，不保存扫描历史

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + TypeScript + Vite |
| 后端 | FastAPI + Python 3.10 |
| 图谱 | NetworkX |
| 向量库 | LanceDB |
| Embedding | sentence-transformers |
| LLM | DeepSeek |
| OCR | 百度智能云 |

## 项目结构

```
medlens-graphrag/
├── backend/           # 后端服务
│   ├── app/          # 应用代码
│   ├── storage/      # 存储目录
│   └── README.md     # 后端文档
├── frontend/         # 前端应用
│   ├── src/         # 源代码
│   └── README.md    # 前端文档
├── environment.yml   # Conda 环境配置
└── README.md        # 本文档
```

## 开发说明

### 后端开发

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### 前端开发

```bash
cd frontend
npm run dev
```

### 构建生产版本

```bash
# 前端
cd frontend
npm run build

# 后端
cd backend
# 使用 gunicorn 等生产级 WSGI 服务器
```

## 许可证

MIT License

## 联系方式

如有问题，请提交 Issue 或联系开发者。

---

**MedLens - 让用药更安全**
