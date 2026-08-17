"""
测试用例自动生成模块
基于 PRD 需求生成可追溯的测试用例
"""
import json
from modules.analyzer import call_llm
from config import Config


def generate_test_cases(prd, reviews, progress_callback=None):
    """
    基于 PRD 生成测试用例
    每个测试用例关联到具体需求和来源评论
    """
    if progress_callback:
        progress_callback("正在生成测试用例...")

    requirements = prd.get("requirements", [])

    system_prompt = """你是一位资深测试工程师，擅长根据产品需求设计测试用例。
请基于以下产品需求，生成详细的测试用例。

要求：
1. 每个测试用例必须关联到具体的需求ID
2. 每个测试用例必须可追溯到来源用户评论ID
3. 包含：用例ID、标题、前置条件、测试步骤、预期结果、优先级、类型
4. 测试类型包括：功能测试、边界测试、异常测试、兼容性测试
5. 验证需求是否真正解决了用户评论中提出的问题
6. 严格返回 JSON 格式，结构如下：
{
  "test_cases": [
    {
      "id": "TC-001",
      "title": "测试用例标题",
      "requirement_id": "REQ-001",
      "source_review_ids": ["id1", "id2"],
      "type": "功能测试",
      "priority": "高",
      "preconditions": "前置条件",
      "steps": ["步骤1", "步骤2"],
      "expected_result": "预期结果",
      "verifies_issue": "该用例验证的用户问题描述"
    }
  ]
}"""

    # 取前 10 个需求生成测试用例，避免 token 超限
    reqs_for_llm = requirements[:10]
    user_prompt = f"""产品需求列表：
{json.dumps(reqs_for_llm, ensure_ascii=False, indent=2)}

请为每个需求生成 2-3 个测试用例。"""

    result = call_llm(system_prompt, user_prompt, temperature=0.3)

    if result:
        try:
            parsed = json.loads(result)
            test_cases = parsed.get("test_cases", [])
            # 为剩余需求生成降级测试用例
            if len(requirements) > 10:
                for req in requirements[10:]:
                    test_cases.extend(fallback_test_cases_for_req(req))
            return {
                "test_cases": test_cases,
                "total_count": len(test_cases),
                "generation_method": "llm_driven",
                "model_used": Config.LLM_MODEL,
            }
        except json.JSONDecodeError:
            print("测试用例 JSON 解析失败，使用降级方案")

    # 全量降级
    all_cases = []
    for req in requirements:
        all_cases.extend(fallback_test_cases_for_req(req))

    return {
        "test_cases": all_cases,
        "total_count": len(all_cases),
        "generation_method": "rule_based_fallback",
        "model_used": "none",
    }


def fallback_test_cases_for_req(req):
    """为单个需求生成降级测试用例"""
    req_id = req.get("id", "REQ-000")
    title = req.get("title", "未知需求")
    source_ids = req.get("source_review_ids", [])

    cases = []
    # 用例1：基础功能验证
    cases.append({
        "id": f"{req_id}-TC01",
        "title": f"验证{title}基础功能",
        "requirement_id": req_id,
        "source_review_ids": source_ids[:3],
        "type": "功能测试",
        "priority": "高",
        "preconditions": "应用已安装并正常启动",
        "steps": [
            "打开应用",
            "进入相关功能页面",
            "执行核心操作流程",
        ],
        "expected_result": f"{title}相关功能正常工作，无报错",
        "verifies_issue": f"验证用户反馈的{title}问题是否解决",
    })

    # 用例2：异常/边界测试
    cases.append({
        "id": f"{req_id}-TC02",
        "title": f"{title}异常场景测试",
        "requirement_id": req_id,
        "source_review_ids": source_ids[:3],
        "type": "异常测试",
        "priority": "中",
        "preconditions": "应用已安装，网络环境异常/弱网",
        "steps": [
            "在弱网环境下打开应用",
            "快速连续操作相关功能",
            "输入边界值数据",
        ],
        "expected_result": "应用不崩溃，给出友好的错误提示",
        "verifies_issue": "验证异常场景下是否会出现用户反馈的问题",
    })

    return cases


def test_cases_to_markdown(test_data):
    """将测试用例转为 Markdown 表格"""
    lines = []
    lines.append("# 测试用例文档")
    lines.append("")
    lines.append(f"**用例总数**：{test_data.get('total_count', 0)}")
    lines.append(f"**生成方式**：{test_data.get('generation_method', 'unknown')}")
    lines.append("")

    lines.append("| 用例ID | 标题 | 关联需求 | 类型 | 优先级 | 预期结果 |")
    lines.append("|--------|------|----------|------|--------|----------|")

    for tc in test_data.get("test_cases", []):
        lines.append(
            f"| {tc['id']} | {tc['title']} | {tc['requirement_id']} | "
            f"{tc['type']} | {tc['priority']} | {tc['expected_result'][:50]} |"
        )

    lines.append("")
    lines.append("## 详细用例")
    lines.append("")

    for tc in test_data.get("test_cases", []):
        lines.append(f"### {tc['id']}：{tc['title']}")
        lines.append("")
        lines.append(f"- **关联需求**：{tc['requirement_id']}")
        lines.append(f"- **测试类型**：{tc['type']}")
        lines.append(f"- **优先级**：{tc['priority']}")
        lines.append(f"- **来源评论**：{', '.join(tc.get('source_review_ids', []))}")
        lines.append(f"- **验证问题**：{tc.get('verifies_issue', '')}")
        lines.append("")
        lines.append(f"**前置条件**：{tc.get('preconditions', '')}")
        lines.append("")
        lines.append("**测试步骤**：")
        for i, step in enumerate(tc.get("steps", []), 1):
            lines.append(f"{i}. {step}")
        lines.append("")
        lines.append(f"**预期结果**：{tc.get('expected_result', '')}")
        lines.append("")

    return "\n".join(lines)
