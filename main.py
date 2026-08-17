"""
Flask 后端主程序
提供 Web 界面和 API 接口
"""
import os
import json
import threading
import uuid
from flask import Flask, render_template, request, jsonify, send_from_directory
from config import Config
from modules import scraper
from modules.pipeline import AnalysisPipeline

app = Flask(__name__)

# 全局任务存储
tasks = {}


def run_analysis(task_id, **kwargs):
    """在后台线程中运行分析流程"""
    pipeline = AnalysisPipeline()
    tasks[task_id]["pipeline"] = pipeline
    try:
        results = pipeline.run(**kwargs)
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["results"] = results
    except Exception as e:
        tasks[task_id]["status"] = "error"
        tasks[task_id]["error"] = str(e)


@app.route("/")
def index():
    """首页"""
    return render_template("index.html", has_llm=Config.has_llm())


@app.route("/api/search", methods=["GET"])
def search_app():
    """搜索应用"""
    keyword = request.args.get("keyword", "").strip()
    country = request.args.get("country", "cn")
    if not keyword:
        return jsonify({"error": "请输入搜索关键词"}), 400

    results = scraper.search_app(keyword, country=country)
    return jsonify({"results": results})


@app.route("/api/analyze", methods=["POST"])
def start_analysis():
    """开始分析"""
    data = request.get_json()
    task_id = str(uuid.uuid4())[:8]

    # 方式1：通过 app_id 抓取
    app_id = data.get("app_id")
    app_name = data.get("app_name", "")
    app_info = data.get("app_info")

    # 方式2：导入数据
    imported_reviews = data.get("imported_reviews")

    if not app_id and not imported_reviews:
        return jsonify({"error": "请提供应用ID或导入评论数据"}), 400

    tasks[task_id] = {
        "status": "running",
        "pipeline": None,
        "results": None,
        "error": None,
    }

    # 启动后台线程
    thread = threading.Thread(
        target=run_analysis,
        kwargs={
            "task_id": task_id,
            "app_id": app_id,
            "app_name": app_name,
            "imported_reviews": imported_reviews,
            "app_info": app_info,
        },
        daemon=True,
    )
    thread.start()

    return jsonify({"task_id": task_id, "status": "running"})


@app.route("/api/progress/<task_id>")
def get_progress(task_id):
    """获取分析进度"""
    task = tasks.get(task_id)
    if not task:
        return jsonify({"error": "任务不存在"}), 404

    pipeline = task.get("pipeline")
    progress = pipeline.get_progress() if pipeline else {"stage": "starting", "logs": []}

    return jsonify({
        "task_id": task_id,
        "status": task["status"],
        "stage": progress["stage"],
        "logs": progress["logs"],
        "error": task.get("error"),
    })


@app.route("/api/results/<task_id>")
def get_results(task_id):
    """获取分析结果"""
    task = tasks.get(task_id)
    if not task:
        return jsonify({"error": "任务不存在"}), 404

    if task["status"] != "completed":
        return jsonify({"error": "分析尚未完成", "status": task["status"]}), 400

    results = task["results"]
    # 不返回完整评论列表（太大），只返回统计和摘要
    response = {
        "app_info": results.get("app_info"),
        "clean_stats": results.get("clean_stats"),
        "distribution": results.get("distribution"),
        "keywords": results.get("keywords"),
        "topics": results.get("topics"),
        "analysis_summary": results.get("analysis_summary"),
        "analysis_method": results.get("analysis_method"),
        "evidence_report": results.get("evidence_report"),
        "prd": results.get("prd"),
        "test_cases": results.get("test_cases"),
        "traceability": results.get("traceability"),
    }
    return jsonify(response)


@app.route("/api/reviews/<task_id>")
def get_reviews(task_id):
    """获取评论数据（分页）"""
    task = tasks.get(task_id)
    if not task or task["status"] != "completed":
        return jsonify({"error": "任务不存在或未完成"}), 404

    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))
    rating_filter = request.args.get("rating", "0")  # 0=全部

    reviews = task["results"].get("cleaned_reviews", [])

    if rating_filter != "0":
        reviews = [r for r in reviews if str(r["rating"]) == rating_filter]

    total = len(reviews)
    start = (page - 1) * per_page
    end = start + per_page
    page_reviews = reviews[start:end]

    return jsonify({
        "total": total,
        "page": page,
        "per_page": per_page,
        "reviews": page_reviews,
    })


@app.route("/api/import", methods=["POST"])
def import_reviews():
    """导入 JSON/CSV 评论文件"""
    if "file" not in request.files:
        return jsonify({"error": "请上传文件"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "文件名为空"}), 400

    # 保存临时文件
    os.makedirs(Config.CACHE_DIR, exist_ok=True)
    filepath = os.path.join(Config.CACHE_DIR, file.filename)
    file.save(filepath)

    try:
        reviews = scraper.load_reviews_from_json_or_csv(filepath)
        return jsonify({
            "success": True,
            "count": len(reviews),
            "reviews": reviews[:5],  # 返回前5条预览
            "all_reviews": reviews,  # 完整数据供前端提交分析
        })
    except Exception as e:
        return jsonify({"error": f"导入失败: {str(e)}"}), 400


@app.route("/output/<path:filename>")
def download_output(filename):
    """下载输出文件"""
    return send_from_directory(Config.OUTPUT_DIR, filename, as_attachment=True)


if __name__ == "__main__":
    print("=" * 60)
    print("  App Store 评论智能分析系统")
    print("=" * 60)
    print(f"  LLM 配置: {'已配置' if Config.has_llm() else '未配置（将使用降级模式）'}")
    print(f"  访问地址: http://localhost:{Config.FLASK_PORT}")
    print("=" * 60)
    app.run(
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=Config.FLASK_DEBUG,
    )
