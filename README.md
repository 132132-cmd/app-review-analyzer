# App Store Review Analyzer

基于用户评论的产品需求智能分析系统，自动抓取 App Store 评论，通过大模型语义分析识别用户痛点，生成可追溯的 PRD 和测试用例。

## 功能特性

- **评论抓取**：基于 Apple 官方 RSS Feed，无需 API Key，支持多地区
- **数据清洗**：自动去重、过滤、结构化，输出评分分布与情感统计
- **语义分析**：LLM 驱动的动态主题发现，支持矛盾反馈识别与证据评估
- **PRD 生成**：自动生成带优先级、版本规划的产品需求，每条需求可追溯到源评论
- **测试用例**：基于需求生成功能/边界/异常测试用例，关联源评论
- **可追溯验证**：校验「评论 → 主题 → 需求 → 测试用例」完整链路
- **数据导入**：支持 JSON/CSV 外部数据集，适配评估场景
- **Web 界面**：实时进度展示，多维度结果可视化

## 技术栈

- 后端：Python + Flask
- 数据：Apple RSS API + JSON 持久化
- AI：OpenAI 兼容接口（支持 DeepSeek / 通义千问 / Kimi 等）
- 前端：原生 HTML / CSS / JavaScript

## 快速开始

### 环境要求

- Python 3.8+
- （可选）LLM API Key

### 安装

```bash
pip install -r requirements.txt
