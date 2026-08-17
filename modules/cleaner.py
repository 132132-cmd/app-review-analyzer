"""
数据清洗和结构化模块
负责去重、过滤、规范化、统计分析
"""
import re
import hashlib
from collections import Counter


def clean_reviews(reviews, progress_callback=None):
    """
    清洗评论数据
    返回清洗后的评论列表和统计信息
    """
    if progress_callback:
        progress_callback(f"开始清洗 {len(reviews)} 条评论...")

    stats = {
        "original_count": len(reviews),
        "removed_empty": 0,
        "removed_duplicate": 0,
        "removed_too_short": 0,
        "final_count": 0,
    }

    cleaned = []
    seen_ids = set()
    seen_content_hashes = set()

    for review in reviews:
        # 1. 过滤空内容
        content = (review.get("content", "") or "").strip()
        title = (review.get("title", "") or "").strip()

        if not content and not title:
            stats["removed_empty"] += 1
            continue

        # 2. 过滤过短内容（少于5个字符且无标题）
        full_text = f"{title} {content}".strip()
        if len(full_text) < 5:
            stats["removed_too_short"] += 1
            continue

        # 3. 基于 review_id 去重
        review_id = review.get("review_id", "")
        if review_id and review_id in seen_ids:
            stats["removed_duplicate"] += 1
            continue
        if review_id:
            seen_ids.add(review_id)

        # 4. 基于内容哈希去重（防止不同 ID 但内容完全相同）
        content_hash = hashlib.md5(full_text.lower().encode()).hexdigest()
        if content_hash in seen_content_hashes:
            stats["removed_duplicate"] += 1
            continue
        seen_content_hashes.add(content_hash)

        # 5. 规范化字段
        cleaned_review = {
            "review_id": review_id or f"gen_{len(cleaned)}",
            "rating": int(review.get("rating", 0) or 0),
            "title": title,
            "content": content,
            "author": review.get("author", "匿名用户"),
            "version": review.get("version", ""),
            "vote_count": int(review.get("vote_count", 0) or 0),
            "full_text": full_text,
            "language": detect_language(full_text),
            "content_length": len(content),
            "is_negative": int(review.get("rating", 0) or 0) <= 2,
            "is_positive": int(review.get("rating", 0) or 0) >= 4,
        }
        cleaned.append(cleaned_review)

    stats["final_count"] = len(cleaned)

    if progress_callback:
        progress_callback(f"清洗完成：原始 {stats['original_count']} 条 → 最终 {stats['final_count']} 条")

    return cleaned, stats


def detect_language(text):
    """简单语言检测：中文字符占比判断"""
    if not text:
        return "unknown"
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    if chinese_chars / len(text) > 0.3:
        return "zh"
    return "en"


def analyze_distribution(reviews):
    """
    分析评论分布统计
    返回评分分布、版本分布、语言分布等
    """
    # 评分分布
    rating_dist = Counter()
    for r in reviews:
        rating_dist[r["rating"]] += 1

    # 版本分布（前10个版本）
    version_dist = Counter()
    for r in reviews:
        if r["version"]:
            version_dist[r["version"]] += 1

    # 语言分布
    lang_dist = Counter()
    for r in reviews:
        lang_dist[r["language"]] += 1

    # 正负评价比例
    negative_count = sum(1 for r in reviews if r["is_negative"])
    positive_count = sum(1 for r in reviews if r["is_positive"])
    neutral_count = len(reviews) - negative_count - positive_count

    # 平均评分
    avg_rating = sum(r["rating"] for r in reviews) / len(reviews) if reviews else 0

    return {
        "total": len(reviews),
        "avg_rating": round(avg_rating, 2),
        "rating_distribution": dict(sorted(rating_dist.items())),
        "version_distribution": dict(version_dist.most_common(10)),
        "language_distribution": dict(lang_dist),
        "sentiment": {
            "positive": positive_count,
            "neutral": neutral_count,
            "negative": negative_count,
            "positive_rate": round(positive_count / len(reviews) * 100, 1) if reviews else 0,
            "negative_rate": round(negative_count / len(reviews) * 100, 1) if reviews else 0,
        }
    }


def extract_keywords(reviews, top_n=20):
    """
    简单关键词提取（基于词频，不依赖外部库）
    对中文做简单的二元分词
    """
    word_freq = Counter()

    for review in reviews:
        text = review["full_text"].lower()
        # 移除标点
        text = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', text)

        if review["language"] == "zh":
            # 中文：提取二元词组
            for i in range(len(text) - 1):
                bigram = text[i:i+2]
                if re.match(r'[\u4e00-\u9fff]{2}', bigram):
                    word_freq[bigram] += 1
        else:
            # 英文：按空格分词
            words = text.split()
            stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                         'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                         'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                         'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
                         'as', 'into', 'through', 'during', 'before', 'after', 'and',
                         'but', 'or', 'nor', 'not', 'so', 'yet', 'both', 'either',
                         'neither', 'each', 'every', 'all', 'any', 'few', 'more',
                         'most', 'other', 'some', 'such', 'no', 'only', 'own', 'same',
                         'than', 'too', 'very', 'just', 'because', 'if', 'when', 'then',
                         'this', 'that', 'these', 'those', 'it', 'its', 'i', 'me',
                         'my', 'we', 'our', 'you', 'your', 'he', 'him', 'his', 'she',
                         'her', 'they', 'them', 'their', 'what', 'which', 'who', 'whom'}
            for word in words:
                if len(word) > 2 and word not in stopwords:
                    word_freq[word] += 1

    return dict(word_freq.most_common(top_n))
