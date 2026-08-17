"""
PRD（产品需求文档）自动生成模块
基于分析出的问题主题，生成可追溯的产品需求
"""
import json
from modules.analyzer import call_llm
from config import Config


def generate_prd(topics, evidence_report, app_info, reviews, progress_callback=None):
    """
    生成 PRD
    topics: 分析出的主题列表
    evidence_report: 证据评估报告
    app_info: 应用信息
    reviews: 评论列表
    返回 PRD 结构化数据
    """
    if progress_callback:
        progress_callback("正在生成产品需求文档（PRD）...")

    # 构建主题摘要供 LLM 使用
    topics_summary = []
    for i, topic in enumerate(topics):
        ev = evidence_report[i] if i < len(evidence_report) else {}
        topics_summary.append({
            "id": f"REQ-{i+1:03d}",
            "name": topic["name"],
            "description": topic["description"],
            "severity": topic.get("severity", "medium"),
            "sample_count": topic.get("sample_count", 0),
            "confidence": topic.get("confidence", 0.5),
            "evidence_sufficiency": ev.get("evidence_sufficiency", "unknown"),
            "review_ids": topic.get("review_ids", [])[:10],
        })

    system_prompt = """你是一位资深产品经理，擅长将用户反馈转化为产品需求。
请基于以下用户问题分析，生成一份结构化的产品需求文档（PRD）。

要求：
1. 每个需求必须可追溯到具体的用户评论ID
2. 明确需求优先级（P0紧急/P1高/P2中/P3低）
3. 进行版本规划（V1.0/V1.1/V2.0）
4. 每个需求包含：需求标题、用户故事、验收标准、来源评论ID
5. 区分"确定性需求"（证据充分）和"假设性需求"（证据不足）
6. 严格返回 JSON 格式，结构如下：
{
  "prd_title": "产品需求文档标题",
  "overview": "需求概览",
  "background": "背景说明",
  "requirements": [
    {
      "id": "REQ-001",
      "title": "需求标题",
      "user_story": "作为用户，我希望...以便...",
      "description": "详细描述",
      "priority": "P0",
      "version": "V1.0",
      "acceptance_criteria": ["标准1", "标准2"],
      "source_review_ids": ["id1", "id2"],
      "evidence_level": "sufficient/limited/insufficient",
      "is_assumption": false,
      "related_topic": "关联主题名称"
    }
  ],
  "version_plan": {
    "V1.0": ["REQ-001"],
    "V1.1": ["REQ-002"],
    "V2.0": ["REQ-003"]
  },
  "risk_and_notes": "风险和注意事项"
}"""

    user_prompt = f"""应用信息：
名称：{app_info.get('name', '未知应用')}
开发者：{app_info.get('developer', '未知')}
分类：{app_info.get('category', '未知')}

分析出的问题主题：
{json.dumps(topics_summary, ensure_ascii=False, indent=2)}

请生成 PRD。"""

    result = call_llm(system_prompt, user_prompt, temperature=0.4)

    if result:
        try:
            prd = json.loads(result)
            prd["generation_method"] = "llm_driven"
            prd["model_used"] = Config.LLM_MODEL
            prd["total_requirements"] = len(prd.get("requirements", []))
            return prd
        except json.JSONDecodeError:
            print("PRD JSON 解析失败，使用降级方案")

    # 降级方案
    return fallback_prd(topics, evidence_report, app_info)


def fallback_prd(topics, evidence_report, app_info):
    """降级 PRD 生成（基于规则）"""
    requirements = []
    version_plan = {"V1.0": [], "V1.1": [], "V2.0": []}

    for i, topic in enumerate(topics):
        ev = evidence_report[i] if i < len(evidence_report) else {}
        req_id = f"REQ-{i+1:03d}"

        # 根据严重程度确定优先级和版本
        severity = topic.get("severity", "medium")
        if severity == "high":
            priority = "P0"
            version = "V1.0"
        elif severity == "medium":
            priority = "P1"
            version = "V1.1"
        else:
            priority = "P2"
            version = "V2.0"

        sufficiency = ev.get("evidence_sufficiency", "limited")

        req = {
            "id": req_id,
            "title": f"优化{topic['name']}",
            "user_story": f"作为用户，我希望{topic['name']}相关问题得到解决，以便获得更好的使用体验",
            "description": topic["description"],
            "priority": priority,
            "version": version,
            "acceptance_criteria": [
                f"解决{topic['name']}相关的用户反馈问题",
                f"相关负面评论数量下降50%以上",
            ],
            "source_review_ids": topic.get("review_ids", [])[:10],
            "evidence_level": sufficiency,
            "is_assumption": sufficiency != "sufficient",
            "related_topic": topic["name"],
        }
        requirements.append(req)
        version_plan[version].append(req_id)

    return {
        "prd_title": f"{app_info.get('name', '应用')}产品需求文档",
        "overview": f"基于{len(topics)}个用户问题主题生成的需求文档（降级方案）",
        "background": "基于 App Store 用户评论分析生成",
        "requirements": requirements,
        "version_plan": version_plan,
        "risk_and_notes": "本 PRD 由规则引擎生成（LLM 不可用），建议人工审核后使用",
        "generation_method": "rule_based_fallback",
        "model_used": "none",
        "total_requirements": len(requirements),
    }


def prd_to_markdown(prd):
    """将 PRD 转为 Markdown 格式，便于导出和阅读"""
    lines = []
    lines.append(f"# {prd.get('prd_title', '产品需求文档')}")
    lines.append("")
    lines.append(f"**生成方式**：{prd.get('generation_method', 'unknown')}")
    lines.append(f"**需求总数**：{prd.get('total_requirements', 0)}")
    lines.append("")

    lines.append("## 1. 背景与概览")
    lines.append("")
    lines.append(prd.get("overview", ""))
    lines.append("")
    lines.append(prd.get("background", ""))
    lines.append("")

    lines.append("## 2. 需求列表")
    lines.append("")
    for req in prd.get("requirements", []):
        lines.append(f"### {req['id']}：{req['title']}")
        lines.append("")
        lines.append(f"- **优先级**：{req['priority']}")
        lines.append(f"- **目标版本**：{req['version']}")
        lines.append(f"- **证据等级**：{req['evidence_level']}")
        lines.append(f"- **是否假设**：{'是' if req.get('is_assumption') else '否'}")
        lines.append(f"- **关联主题**：{req.get('related_topic', '')}")
        lines.append("")
        lines.append(f"**用户故事**：{req.get('user_story', '')}")
        lines.append("")
        lines.append(f"**描述**：{req.get('description', '')}")
        lines.append("")
        lines.append("**验收标准**：")
        for ac in req.get("acceptance_criteria", []):
            lines.append(f"- {ac}")
        lines.append("")
        lines.append(f"**来源评论ID**：{', '.join(req.get('source_review_ids', []))}")
        lines.append("")

    lines.append("## 3. 版本规划")
    lines.append("")
    for version, reqs in prd.get("version_plan", {}).items():
        lines.append(f"### {version}")
        for rid in reqs:
            lines.append(f"- {rid}")
        lines.append("")

    lines.append("## 4. 风险与注意事项")
    lines.append("")
    lines.append(prd.get("risk_and_notes", ""))
    lines.append("")

    return "\n".join(lines)
