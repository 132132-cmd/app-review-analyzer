"""
可追溯性验证模块
验证从用户评论 → 问题发现 → 需求 → 测试用例的完整追溯链
"""


def verify_traceability(reviews, topics, prd, test_data, progress_callback=None):
    """
    验证完整的可追溯链
    返回验证报告，包含通过/失败/警告项
    """
    if progress_callback:
        progress_callback("正在验证可追溯链...")

    report = {
        "total_checks": 0,
        "passed": 0,
        "failed": 0,
        "warnings": 0,
        "details": [],
        "traceability_matrix": [],
    }

    all_review_ids = {r["review_id"] for r in reviews}

    # 检查1：每个主题是否有关联评论
    for topic in topics:
        report["total_checks"] += 1
        linked_ids = [rid for rid in topic.get("review_ids", []) if rid in all_review_ids]
        if linked_ids:
            report["passed"] += 1
            report["details"].append({
                "check": f"主题「{topic['name']}」关联评论",
                "status": "pass",
                "linked_count": len(linked_ids),
            })
        else:
            report["failed"] += 1
            report["details"].append({
                "check": f"主题「{topic['name']}」关联评论",
                "status": "fail",
                "message": "该主题没有关联到任何有效评论，结论可能无根据",
            })

    # 检查2：每个需求是否有来源评论
    requirements = prd.get("requirements", [])
    for req in requirements:
        report["total_checks"] += 1
        source_ids = [rid for rid in req.get("source_review_ids", []) if rid in all_review_ids]
        if source_ids:
            report["passed"] += 1
            report["details"].append({
                "check": f"需求「{req['id']}」来源评论",
                "status": "pass",
                "linked_count": len(source_ids),
            })
        else:
            if req.get("is_assumption"):
                report["warnings"] += 1
                report["details"].append({
                    "check": f"需求「{req['id']}」来源评论",
                    "status": "warning",
                    "message": "该需求标记为假设性需求，无直接评论来源",
                })
            else:
                report["failed"] += 1
                report["details"].append({
                    "check": f"需求「{req['id']}」来源评论",
                    "status": "fail",
                    "message": "该需求没有来源评论且未标记为假设",
                })

    # 检查3：每个测试用例是否关联需求和评论
    test_cases = test_data.get("test_cases", [])
    req_ids = {req["id"] for req in requirements}
    for tc in test_cases:
        report["total_checks"] += 1
        has_req = tc.get("requirement_id") in req_ids
        has_source = bool([rid for rid in tc.get("source_review_ids", []) if rid in all_review_ids])

        if has_req and has_source:
            report["passed"] += 1
            report["details"].append({
                "check": f"测试用例「{tc['id']}」追溯链",
                "status": "pass",
            })
        elif has_req and not has_source:
            report["warnings"] += 1
            report["details"].append({
                "check": f"测试用例「{tc['id']}」追溯链",
                "status": "warning",
                "message": "关联了需求但缺少直接评论来源",
            })
        else:
            report["failed"] += 1
            report["details"].append({
                "check": f"测试用例「{tc['id']}」追溯链",
                "status": "fail",
                "message": "未关联到有效需求",
            })

    # 构建追溯矩阵
    for req in requirements:
        related_tests = [tc["id"] for tc in test_cases if tc.get("requirement_id") == req["id"]]
        source_ids = [rid for rid in req.get("source_review_ids", []) if rid in all_review_ids]
        related_topic = req.get("related_topic", "")

        report["traceability_matrix"].append({
            "requirement_id": req["id"],
            "requirement_title": req["title"],
            "related_topic": related_topic,
            "source_review_count": len(source_ids),
            "source_review_ids": source_ids,
            "test_case_count": len(related_tests),
            "test_case_ids": related_tests,
            "chain_complete": bool(source_ids) and bool(related_tests),
        })

    # 总体结论
    if report["failed"] == 0:
        report["conclusion"] = "通过"
        report["conclusion_detail"] = "所有追溯链完整，无无根据的结论"
    elif report["failed"] < report["total_checks"] * 0.1:
        report["conclusion"] = "基本通过"
        report["conclusion_detail"] = f"存在 {report['failed']} 项追溯缺失，建议修正"
    else:
        report["conclusion"] = "不通过"
        report["conclusion_detail"] = f"存在 {report['failed']} 项严重追溯缺失，需要修正"

    return report


def find_orphan_conclusions(topics, prd):
    """
    查找没有证据支持的结论（孤儿结论）
    返回需要删除、修正或标记为假设的条目
    """
    orphans = []

    for topic in topics:
        if not topic.get("review_ids"):
            orphans.append({
                "type": "topic",
                "id": topic.get("name"),
                "issue": "主题没有关联评论",
                "action": "建议删除或标记为假设",
            })

    for req in prd.get("requirements", []):
        if not req.get("source_review_ids") and not req.get("is_assumption"):
            orphans.append({
                "type": "requirement",
                "id": req.get("id"),
                "issue": "需求没有来源评论且未标记为假设",
                "action": "建议补充来源或标记为假设",
            })

    return orphans
