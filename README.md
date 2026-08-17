# App Store 评论智能分析系统

> 从真实用户评论到可执行产品计划的全链路 AI 分析平台

## 项目简介

本系统能够自动抓取 App Store 的用户评论，通过 AI 大模型进行语义分析，自动识别用户痛点、生成产品需求文档（PRD）和测试用例，并验证从评论到需求到测试的完整可追溯链。

### 核心功能

1. **数据收集**：通过 Apple 官方 RSS 接口抓取 App Store 评论，无需爬虫 API Key
2. **数据清洗**：自动去重、过滤空内容、结构化处理、统计分析
3. **AI 语义分析**：大模型驱动的动态主题发现，超越固定关键词匹配
4. **PRD 自动生成**：基于用户问题生成带优先级和版本规划的产品需求
5. **测试用例生成**：为每个需求生成可追溯的测试用例
6. **可追溯性验证**：验证「评论 → 发现 → 需求 → 测试用例」的完整链路
7. **数据导入**：支持 JSON/CSV 格式外部数据集导入
8. **可视化界面**：Web 界面实时展示分析进度和结果

---

## 快速开始（电脑小白版）

### 第一步：安装 Python

1. 打开浏览器，访问 https://www.python.org/downloads/
2. 点击黄色的 "Download Python 3.x.x" 按钮下载
3. 双击下载的安装包
4. **重要**：安装界面底部勾选 "Add Python to PATH"（添加到环境变量）
5. 点击 "Install Now" 等待安装完成
6. 验证：按 `Win + R`，输入 `cmd` 回车，在黑窗口中输入 `python --version`，能看到版本号就说明成功了

### 第二步：下载项目代码

将本项目文件夹放到一个你能找到的位置，比如 `D:\app-review-analyzer`

### 第三步：安装依赖

1. 打开项目文件夹
2. 在文件夹地址栏输入 `cmd` 然后回车（会打开一个黑窗口，路径已经在当前文件夹）
3. 输入以下命令并回车：

```bash
pip install -r requirements.txt
```

4. 等待安装完成（看到 Successfully installed 就说明好了）

### 第四步：配置 AI 模型（可选但强烈推荐）

> 不配置也能运行，但会使用降级模式（基于关键词规则），分析质量会差很多。

1. 在项目文件夹中，复制 `.env.example` 文件，改名为 `.env`
2. 用记事本打开 `.env` 文件
3. 填入你的 AI API 信息：

```
LLM_API_KEY=你的API密钥
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
```

**支持的 AI 平台（任选其一）：**

| 平台 | BASE_URL | 推荐模型 | 获取地址 |
|------|----------|----------|----------|
| OpenAI | https://api.openai.com/v1 | gpt-4o-mini | platform.openai.com |
| DeepSeek | https://api.deepseek.com/v1 | deepseek-chat | platform.deepseek.com |
| 通义千问 | https://dashscope.aliyuncs.com/compatible-mode/v1 | qwen-turbo | dashscope.aliyun.com |
| Kimi | https://api.moonshot.cn/v1 | moonshot-v1-8k | platform.moonshot.cn |

> 推荐用 DeepSeek，便宜好用，新用户有免费额度。

### 第五步：启动程序

1. 在项目文件夹的地址栏输入 `cmd` 回车
2. 输入以下命令并回车：

```bash
python main.py
```

3. 看到类似下面的输出就说明启动成功了：

```
============================================================
  App Store 评论智能分析系统
============================================================
  LLM 配置: 已配置
  访问地址: http://localhost:5000
============================================================
```

4. 打开浏览器，访问 `http://localhost:5000`

### 第六步：使用系统

1. **搜索应用**：在搜索框输入应用名称（如"微信"），点击搜索
2. **选择应用**：在搜索结果中点击你想分析的应用旁边的"开始分析"按钮
3. **等待分析**：系统会自动执行 6 个阶段，实时显示进度日志
4. **查看结果**：分析完成后，页面会展示：
   - 分析概览（数据统计）
   - 评论数据统计（评分分布、情感分析、热门关键词）
   - AI 问题主题分析
   - 产品需求文档（PRD）
   - 测试用例
   - 可追溯性验证
   - 评论详情（可按评分筛选）

### 导入外部数据

如果面试官提供了 JSON 或 CSV 格式的评论数据集：

1. 切换到"导入数据"标签页
2. 点击选择文件，上传数据集
3. 预览确认后点击"开始分析导入数据"

**CSV 文件格式要求（列名）：**
- `review_id`：评论ID（可选）
- `rating`：评分（1-5）
- `title`：标题（可选）
- `content`：评论内容
- `author`：作者（可选）
- `version`：版本（可选）

---

## 项目结构

```
app-review-analyzer/
├── main.py                  # Flask 后端主程序
├── config.py                # 配置管理
├── requirements.txt         # Python 依赖
├── .env.example             # 环境变量示例
├── README.md                # 说明文档
├── modules/
│   ├── __init__.py
│   ├── scraper.py           # App Store 评论抓取
│   ├── cleaner.py           # 数据清洗和结构化
│   ├── analyzer.py          # LLM 语义分析（核心AI模块）
│   ├── prd_generator.py     # PRD 自动生成
│   ├── test_generator.py    # 测试用例生成
│   ├── traceability.py      # 可追溯性验证
│   └── pipeline.py          # 主流程编排
├── templates/
│   └── index.html           # 前端页面
├── static/
│   ├── css/style.css        # 样式
│   └── js/app.js            # 前端逻辑
├── data/                    # 抓取的原始数据
├── output/                  # 分析结果输出（PRD.md、测试用例.md）
└── cache/                   # 临时缓存
```

---

## 技术说明

### 数据来源

使用 Apple 官方 RSS Feed：
- 搜索：`https://itunes.apple.com/search`
- 评论：`https://itunes.apple.com/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json`

无需 API Key，每页 50 条，最多抓取 500 条。遵守请求速率限制（默认 1 秒间隔）。

### AI 语义分析

- 核心任务（主题发现、需求生成、测试用例生成）由 LLM 大模型驱动
- 数据收集、去重、字段规范化使用确定性规则
- LLM 不可用时自动降级到规则模式，并明确标注
- 每项发现包含来源评论ID、样本数量、置信度、矛盾证据说明

### 可追溯性

每个需求和测试用例都关联到具体的用户评论ID，系统自动验证追溯链完整性，无根据的结论会被标记或警告。

---

## 常见问题

**Q: 启动后浏览器打不开页面？**
A: 确认黑窗口还开着（关闭窗口程序就停了），确认地址是 `http://localhost:5000`

**Q: 提示 "LLM 未配置"？**
A: 不影响使用，只是会用降级模式。想要更好的分析效果，按第四步配置 API Key

**Q: 抓取评论失败？**
A: 可能是网络问题或 Apple 接口限流，稍等重试，或使用导入数据功能

**Q: 分析很慢？**
A: AI 分析需要调用大模型 API，取决于网络和模型响应速度，通常 1-3 分钟

**Q: 怎么停止程序？**
A: 在黑窗口中按 `Ctrl + C`

---

## 交付说明

- 本项目可在本地直接运行
- 分析结果自动保存到 `output/` 目录（JSON + Markdown 格式）
- 支持外部数据集导入，不硬编码特定应用
- 完整提交历史请查看 Git 记录
