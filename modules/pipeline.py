"""
主流程编排模块
串联：抓取 → 清洗 → 分析 → PRD → 测试用例 → 可追溯验证
"""
import os
import json
import time
from config import Config
from modules import scraper, cleaner, analyzer, prd_generator, test_generator, traceability


class AnalysisPipeline:
    """分析流程编排器"""

    def __init__(self):
        self.progress_log = []
        self.current_stage = "idle"
        self.results = {}

    def log(self, message):
        """记录进度日志"""
        timestamp = time.strftime("%H:%M:%S")
        entry = {"time": timestamp, "message": message}
        self.progress_log.append(entry)
        print(f"[{timestamp}] {message}")
        return entry

    def run(self, app_id=None, app_name="", imported_reviews=None, app_info=None):
        """
        执行完整分析流程
        app_id: App Store 应用 ID（用于抓取）
        imported_reviews: 导入的评论数据（可选，用于外部数据集）
        app_info: 应用信息（可选）
        """
        self.progress_log = []
        self.results = {}

        try:
            # ========== 阶段1：确定分析范围 & 收集数据 ==========
            self.current_stage = "data_collection"
            self.log("=== 阶段1：数据收集 ===")

            if imported_reviews:
                self.log(f"使用导入的评论数据，共 {len(imported_reviews)} 条")
                raw_reviews = imported_reviews
                if not app_info:
                    app_info = {"name": app_name or "导入数据集", "app_id": "imported"}
            else:
                if not app_id:
                    raise ValueError("请提供应用ID或导入评论数据")

                self.log(f"开始抓取 App ID: {app_id} 的评论...")
                raw_reviews = scraper.fetch_reviews(
                    app_id,
                    max_pages=10,
                    progress_callback=lambda msg: self.log(msg)
                )
                self.log(f"抓取完成，共获取 {len(raw_reviews)} 条原始评论")

                if not app_info:
                    app_info = {"name": app_name or f"App_{app_id}", "app_id": app_id}

            if not raw_reviews:
                raise ValueError("未获取到任何评论数据")

            self.results["raw_reviews"] = raw_reviews
            self.results["app_info"] = app_info

            # ========== 阶段2：数据清洗 ==========
            self.current_stage = "cleaning"
            self.log("=== 阶段2：数据清洗与结构化 ===")

            cleaned_reviews, clean_stats = cleaner.clean_reviews(
                raw_reviews,
                progress_callback=lambda msg: self.log(msg)
            )
            self.results["cleaned_reviews"] = cleaned_reviews
            self.results["clean_stats"] = clean_stats

            # 统计分布
            distribution = cleaner.analyze_distribution(cleaned_reviews)
            keywords = cleaner.extract_keywords(cleaned_reviews)
            self.results["distribution"] = distribution
            self.results["keywords"] = keywords
            self.log(f"清洗后有效评论: {clean_stats['final_count']} 条")
            self.log(f"平均评分: {distribution['avg_rating']}，负面率: {distribution['sentiment']['negative_rate']}%")

            # ========== 阶段3：AI 语义分析 ==========
            self.current_stage = "analysis"
            self.log("=== 阶段3：AI 语义分析（动态主题发现）===")

            analysis_result = analyzer.analyze_topics(
                cleaned_reviews,
                progress_callback=lambda msg: self.log(msg)
            )
            topics = analysis_result.get("topics", [])
            self.results["topics"] = topics
            self.results["analysis_summary"] = analysis_result.get("summary", "")
            self.results["analysis_method"] = analysis_result.get("analysis_method", "")
            self.log(f"发现 {len(topics)} 个问题主题")
            self.log(f"分析方式: {analysis_result.get('analysis_method', 'unknown')}")

            # 证据评估
            evidence_report = analyzer.analyze_evidence(
                cleaned_reviews, topics,
                progress_callback=lambda msg: self.log(msg)
            )
            self.results["evidence_report"] = evidence_report

            # ========== 阶段4：生成 PRD ==========
            self.current_stage = "prd_generation"
            self.log("=== 阶段4：生成产品需求文档（PRD）===")

            prd = prd_generator.generate_prd(
                topics, evidence_report, app_info, cleaned_reviews,
                progress_callback=lambda msg: self.log(msg)
            )
            self.results["prd"] = prd
            self.log(f"生成 {prd.get('total_requirements', 0)} 条需求")

            # ========== 阶段5：生成测试用例 ==========
            self.current_stage = "test_generation"
            self.log("=== 阶段5：生成测试用例 ===")

            test_data = test_generator.generate_test_cases(
                prd, cleaned_reviews,
                progress_callback=lambda msg: self.log(msg)
            )
            self.results["test_cases"] = test_data
            self.log(f"生成 {test_data.get('total_count', 0)} 条测试用例")

            # ========== 阶段6：可追溯性验证 ==========
            self.current_stage = "traceability"
            self.log("=== 阶段6：可追溯性验证 ===")

            trace_report = traceability.verify_traceability(
                cleaned_reviews, topics, prd, test_data,
                progress_callback=lambda msg: self.log(msg)
            )
            self.results["traceability"] = trace_report
            self.log(f"可追溯验证结论: {trace_report['conclusion']}")
            self.log(f"通过: {trace_report['passed']}，失败: {trace_report['failed']}，警告: {trace_report['warnings']}")

            # ========== 完成 ==========
            self.current_stage = "completed"
            self.log("=== 分析流程全部完成 ===")

            # 保存结果
            self.save_results()

            return self.results

        except Exception as e:
            self.current_stage = "error"
            self.log(f"流程出错: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            raise

    def save_results(self):
        """保存结果到文件"""
        os.makedirs(Config.OUTPUT_DIR, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        app_name = self.results.get("app_info", {}).get("name", "analysis")
        safe_name = "".join(c for c in app_name if c.isalnum() or c in ("-", "_"))[:30]

        # 保存完整结果
        result_file = os.path.join(Config.OUTPUT_DIR, f"{safe_name}_{timestamp}.json")
        # 移除不可序列化的内容
        save_data = {k: v for k, v in self.results.items() if k != "raw_reviews"}
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2, default=str)

        # 保存 PRD Markdown
        if "prd" in self.results:
            prd_md = prd_generator.prd_to_markdown(self.results["prd"])
            prd_file = os.path.join(Config.OUTPUT_DIR, f"{safe_name}_PRD_{timestamp}.md")
            with open(prd_file, "w", encoding="utf-8") as f:
                f.write(prd_md)

        # 保存测试用例 Markdown
        if "test_cases" in self.results:
            tc_md = test_generator.test_cases_to_markdown(self.results["test_cases"])
            tc_file = os.path.join(Config.OUTPUT_DIR, f"{safe_name}_测试用例_{timestamp}.md")
            with open(tc_file, "w", encoding="utf-8") as f:
                f.write(tc_md)

        self.log(f"结果已保存到 {Config.OUTPUT_DIR}")

    def get_progress(self):
        """获取当前进度"""
        return {
            "stage": self.current_stage,
            "logs": self.progress_log,
            "has_results": bool(self.results),
        }
