"""
LLM 语义分析模块（核心 AI 模块）
负责动态主题发现、问题分类、基于证据的分析、矛盾识别
"""
import json
import re
import requests
from config import Config


def call_llm(system_prompt, user_prompt, temperature=0.3):
    """
    调用 LLM API（兼容 OpenAI 格式，使用 requests 直接调用，无需 openai 包）
    返回模型生成的文本
    """
    if not Config.has_llm():
        return None

    try:
        url = Config.LLM_BASE_URL.rstrip("/") + "/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Config.LLM_API_KEY}",
        }
        data = {
            "model": Config.LLM_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        resp = requests.post(url, headers=headers, json=data, timeout=120)
        resp.raise_for_status()
        result = resp.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"LLM 调用失败: {e}")
        return None


def analyze_topics(reviews, progress_callback=None):
    """
    动态主题发现和问题分类
    使用 LLM 对评论进行语义聚类，识别主要问题主题
    返回主题列表，每个主题包含：名称、描述、相关评论ID、严重程度、置信度
    """
    if progress_callback:
        progress_callback("正在进行 AI 语义分析（主题发现）...")

    # 优先分析负面评论（1-2星），因为问题主要来自负面反馈
    negative_reviews = [r for r in reviews if r["is_negative"]]
    if not negative_reviews:
        negative_reviews = reviews[:100]  # 如果没有负面评论，取前100条

    # 限制发送给 LLM 的评论数量，避免 token 超限
    # 取评分最低的前 80 条
    sorted_reviews = sorted(negative_reviews, key=lambda x: x["rating"])
    sample_reviews = sorted_reviews[:80]

    # 构建评论文本
    review_texts = []
    for r in sample_reviews:
        review_texts.append(f"[ID:{r['review_id']}] [评分:{r['rating']}星] {r['full_text'][:200]}")

    reviews_block = "\n\n".join(review_texts)

    system_prompt = """你是一位专业的产品分析师，擅长从用户评论中发现产品问题。
请对以下用户评论进行语义分析，动态识别主要问题主题。
要求：
1. 不要使用预设的固定分类，根据评论内容动态发现主题
2. 每个主题需要包含：主题名称、详细描述、相关评论ID列表、严重程度(high/medium/low)、置信度(0-1)
3. 识别评论中的矛盾反馈（同一问题有不同评价）
4. 标注证据不足的主题
5. 严格返回 JSON 格式，结构如下：
{
  "topics": [
    {
      "name": "主题名称",
      "description": "详细描述",
      "review_ids": ["id1", "id2"],
      "sample_count": 5,
      "severity": "high",
      "confidence": 0.85,
      "contradictions": "是否存在矛盾反馈及说明",
      "evidence_note": "证据充分性说明"
    }
  ],
  "summary": "整体分析摘要"
}"""

    user_prompt = f"以下是用户评论数据，请进行主题分析：\n\n{reviews_block}"

    result = call_llm(system_prompt, user_prompt)

    if result:
        try:
            parsed = json.loads(result)
            # 验证并补全主题的实际评论引用
            topics = parsed.get("topics", [])
            for topic in topics:
                topic["review_ids"] = [rid for rid in topic.get("review_ids", [])
                                       if any(r["review_id"] == rid for r in reviews)]
                topic["actual_sample_count"] = len(topic["review_ids"])
            parsed["topics"] = topics
            parsed["analysis_method"] = "llm_driven"
            parsed["model_used"] = Config.LLM_MODEL
            return parsed
        except json.JSONDecodeError:
            print("LLM 返回的 JSON 解析失败，使用降级方案")

    # 降级方案：基于关键词的简单分类（当 LLM 不可用时）
    return fallback_topic_analysis(reviews)


def fallback_topic_analysis(reviews):
    """
    降级方案：基于规则的简单主题分析
    当 LLM 不可用时使用，明确标注为规则驱动
    """
    # 定义一些常见问题关键词
    keyword_topics = {
        "崩溃/闪退问题": ["闪退", "崩溃", "卡住", "死机", "黑屏", "crash", "freeze", "bug"],
        "登录/账号问题": ["登录", "注册", "账号", "密码", "验证码", "login", "account", "password"],
        "支付/收费问题": ["收费", "扣费", "会员", "充值", "付款", "支付", "vip", "pay", "subscription"],
        "广告过多": ["广告", "弹窗", "推广", "ad", "advertisement", "popup"],
        "性能/卡顿": ["卡顿", "慢", "加载", "延迟", "lag", "slow", "loading"],
        "功能缺失": ["没有", "不能", "无法", "缺少", "希望", "建议", "missing", "can't", "cannot"],
        "界面/体验": ["界面", "ui", "设计", "难看", "体验", "ux", "design"],
        "客服/售后": ["客服", "售后", "退款", "投诉", "service", "refund"],
    }

    topics = []
    for topic_name, keywords in keyword_topics.items():
        matched = []
        for r in reviews:
            text = r["full_text"].lower()
            if any(kw.lower() in text for kw in keywords):
                matched.append(r["review_id"])
        if matched:
            # 计算严重程度（基于负面评论比例）
            neg_count = sum(1 for rid in matched
                          for r in reviews if r["review_id"] == rid and r["is_negative"])
            severity = "high" if neg_count / len(matched) > 0.6 else ("medium" if neg_count / len(matched) > 0.3 else "low")
            topics.append({
                "name": topic_name,
                "description": f"涉及{topic_name}相关的用户反馈",
                "review_ids": matched[:20],
                "sample_count": len(matched),
                "actual_sample_count": min(len(matched), 20),
                "severity": severity,
                "confidence": 0.5,
                "contradictions": "规则匹配，未进行矛盾分析",
                "evidence_note": "基于关键词匹配，可能存在误判",
            })

    return {
        "topics": sorted(topics, key=lambda x: x["sample_count"], reverse=True)[:8],
        "summary": "基于关键词规则的降级分析（LLM 不可用），结果仅供参考",
        "analysis_method": "rule_based_fallback",
        "model_used": "none",
    }


def analyze_evidence(reviews, topics, progress_callback=None):
    """
    评估证据充分性，识别矛盾反馈和不确定性
    """
    if progress_callback:
        progress_callback("正在评估证据充分性和矛盾反馈...")

    evidence_report = []
    for topic in topics:
        topic_reviews = [r for r in reviews if r["review_id"] in topic.get("review_ids", [])]

        if not topic_reviews:
            evidence_report.append({
                "topic": topic["name"],
                "status": "no_evidence",
                "note": "未找到匹配的评论",
            })
            continue

        ratings = [r["rating"] for r in topic_reviews]
        has_positive = any(r >= 4 for r in ratings)
        has_negative = any(r <= 2 for r in ratings)

        # 检查是否有矛盾
        contradiction = ""
        if has_positive and has_negative:
            contradiction = f"该主题同时存在正面({sum(1 for r in ratings if r>=4)}条)和负面({sum(1 for r in ratings if r<=2)}条)反馈"

        # 证据充分性评估
        sample_count = len(topic_reviews)
        if sample_count >= 10:
            sufficiency = "sufficient"
        elif sample_count >= 3:
            sufficiency = "limited"
        else:
            sufficiency = "insufficient"

        evidence_report.append({
            "topic": topic["name"],
            "sample_count": sample_count,
            "rating_range": [min(ratings), max(ratings)],
            "avg_rating": round(sum(ratings) / len(ratings), 2),
            "has_contradiction": has_positive and has_negative,
            "contradiction_detail": contradiction,
            "evidence_sufficiency": sufficiency,
            "confidence": topic.get("confidence", 0.5),
        })

    return evidence_report
