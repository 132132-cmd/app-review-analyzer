"""
App Store 评论抓取模块
使用 Apple 官方 RSS Feed，无需 API Key
"""
import requests
import time
import json
import os
from config import Config


def search_app(keyword, country="cn", limit=10):
    """
    搜索 App Store 应用
    返回应用列表，包含 app_id、名称、图标、开发者等
    """
    url = "https://itunes.apple.com/search"
    params = {
        "term": keyword,
        "entity": "software",
        "country": country,
        "limit": limit
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("results", []):
            results.append({
                "app_id": item.get("trackId"),
                "name": item.get("trackName"),
                "developer": item.get("artistName"),
                "icon": item.get("artworkUrl100"),
                "url": item.get("trackViewUrl"),
                "rating": item.get("averageUserRating"),
                "rating_count": item.get("userRatingCount"),
                "category": item.get("primaryGenreName"),
            })
        return results
    except Exception as e:
        print(f"搜索应用失败: {e}")
        return []


def fetch_reviews(app_id, country="cn", max_pages=10, progress_callback=None):
    """
    抓取 App Store 评论
    app_id: 应用 ID（数字）
    country: 国家代码，默认 cn
    max_pages: 最多抓取页数，每页50条
    返回评论列表
    """
    all_reviews = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    for page in range(1, max_pages + 1):
        url = f"https://itunes.apple.com/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json"

        if progress_callback:
            progress_callback(f"正在抓取第 {page}/{max_pages} 页评论...")

        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            feed = data.get("feed", {})
            entries = feed.get("entry", [])

            # 第一条是应用信息，跳过
            if page == 1 and entries:
                entries = entries[1:]

            if not entries:
                break

            for entry in entries:
                review = parse_review_entry(entry)
                if review:
                    all_reviews.append(review)

        except Exception as e:
            print(f"抓取第 {page} 页失败: {e}")
            break

        time.sleep(Config.REQUEST_DELAY)

    return all_reviews


def parse_review_entry(entry):
    """解析单条评论"""
    try:
        # 评论 ID
        review_id = entry.get("id", {}).get("label", "")

        # 评分
        rating = 0
        if "im:rating" in entry:
            rating = int(entry["im:rating"].get("label", 0))

        # 标题
        title = entry.get("title", {}).get("label", "")

        # 内容
        content = entry.get("content", {}).get("label", "")

        # 作者
        author = entry.get("author", {}).get("name", {}).get("label", "匿名用户")

        # 版本
        version = ""
        if "im:version" in entry:
            version = entry["im:version"].get("label", "")

        # 投票数
        vote_count = 0
        if "im:voteCount" in entry:
            vote_count = int(entry["im:voteCount"].get("label", 0))

        return {
            "review_id": review_id,
            "rating": rating,
            "title": title,
            "content": content,
            "author": author,
            "version": version,
            "vote_count": vote_count,
        }
    except Exception as e:
        print(f"解析评论失败: {e}")
        return None


def save_reviews(reviews, app_id, app_name=""):
    """保存评论到 JSON 文件"""
    os.makedirs(Config.DATA_DIR, exist_ok=True)
    filename = f"reviews_{app_id}.json"
    filepath = os.path.join(Config.DATA_DIR, filename)
    data = {
        "app_id": app_id,
        "app_name": app_name,
        "total": len(reviews),
        "reviews": reviews
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filepath


def load_reviews(filepath):
    """从 JSON 文件加载评论"""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def load_reviews_from_json_or_csv(filepath):
    """
    从 JSON 或 CSV 文件导入评论数据
    支持面试官提供的外部数据集
    """
    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".json":
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 兼容两种格式：直接是列表，或包含 reviews 字段
        if isinstance(data, list):
            return data
        return data.get("reviews", data.get("data", []))

    elif ext == ".csv":
        import csv
        reviews = []
        with open(filepath, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                review = {
                    "review_id": row.get("review_id", row.get("id", f"imported_{i}")),
                    "rating": int(row.get("rating", row.get("score", 0)) or 0),
                    "title": row.get("title", ""),
                    "content": row.get("content", row.get("review", row.get("text", ""))),
                    "author": row.get("author", row.get("user", "导入用户")),
                    "version": row.get("version", ""),
                    "vote_count": int(row.get("vote_count", 0) or 0),
                }
                reviews.append(review)
        return reviews

    else:
        raise ValueError(f"不支持的文件格式: {ext}，仅支持 .json 和 .csv")
