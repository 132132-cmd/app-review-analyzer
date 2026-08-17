// 全局状态
let currentTaskId = null;
let currentResults = null;
let currentReviewPage = 1;
let currentRatingFilter = "0";
let importedReviewsData = null;
let progressInterval = null;

// Tab 切换
document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
        document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
        btn.classList.add("active");
        document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
    });
});

// 搜索应用
async function searchApp() {
    const keyword = document.getElementById("search-input").value.trim();
    const country = document.getElementById("country-select").value;
    if (!keyword) { alert("请输入应用名称"); return; }

    const container = document.getElementById("search-results");
    container.innerHTML = '<div class="spinner"></div>搜索中...';

    try {
        const resp = await fetch(`/api/search?keyword=${encodeURIComponent(keyword)}&country=${country}`);
        const data = await resp.json();
        if (data.error) { container.innerHTML = `<p style="color:red">${data.error}</p>`; return; }

        if (data.results.length === 0) {
            container.innerHTML = "<p>未找到相关应用</p>";
            return;
        }

        container.innerHTML = data.results.map(app => `
            <div class="app-item">
                <img src="${app.icon || ''}" alt="" onerror="this.style.display='none'">
                <div class="app-info">
                    <h4>${app.name}</h4>
                    <p>${app.developer} · ${app.category || ''} · 评分: ${app.rating || 'N/A'} (${app.rating_count || 0}条评价)</p>
                </div>
                <button class="btn btn-primary btn-sm" onclick='startAnalysis(${JSON.stringify(app).replace(/'/g, "&#39;")})'>开始分析</button>
            </div>
        `).join("");
    } catch (e) {
        container.innerHTML = `<p style="color:red">搜索失败: ${e.message}</p>`;
    }
}

// 导入评论
async function importReviews() {
    const fileInput = document.getElementById("import-file");
    if (!fileInput.files[0]) { alert("请选择文件"); return; }

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    const preview = document.getElementById("import-preview");
    preview.innerHTML = '<div class="spinner"></div>导入中...';

    try {
        const resp = await fetch("/api/import", { method: "POST", body: formData });
        const data = await resp.json();
        if (data.error) { preview.innerHTML = `<p style="color:red">${data.error}</p>`; return; }

        importedReviewsData = data.all_reviews;
        preview.innerHTML = `
            <p>成功导入 <strong>${data.count}</strong> 条评论</p>
            <div style="margin:12px 0">
                <strong>预览（前5条）：</strong>
                ${data.reviews.map(r => `
                    <div class="review-item">
                        <div class="review-header">
                            <span class="review-author">${r.author}</span>
                            <span class="review-rating">${'★'.repeat(r.rating)}${'☆'.repeat(5-r.rating)}</span>
                        </div>
                        <div class="review-content">${(r.content || r.title || '').substring(0, 100)}</div>
                    </div>
                `).join("")}
            </div>
            <button class="btn btn-success" onclick="startImportedAnalysis()">开始分析导入数据</button>
        `;
    } catch (e) {
        preview.innerHTML = `<p style="color:red">导入失败: ${e.message}</p>`;
    }
}

// 开始分析（搜索方式）
async function startAnalysis(app) {
    document.getElementById("input-section").classList.add("hidden");
    document.getElementById("progress-section").classList.remove("hidden");
    document.getElementById("results-section").classList.add("hidden");
    document.getElementById("progress-log").innerHTML = "";

    try {
        const resp = await fetch("/api/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                app_id: app.app_id,
                app_name: app.name,
                app_info: app,
            }),
        });
        const data = await resp.json();
        if (data.error) { alert(data.error); return; }
        currentTaskId = data.task_id;
        pollProgress();
    } catch (e) {
        alert("启动分析失败: " + e.message);
    }
}

// 开始分析（导入方式）
async function startImportedAnalysis() {
    if (!importedReviewsData) { alert("请先导入数据"); return; }

    document.getElementById("input-section").classList.add("hidden");
    document.getElementById("progress-section").classList.remove("hidden");
    document.getElementById("results-section").classList.add("hidden");
    document.getElementById("progress-log").innerHTML = "";

    try {
        const resp = await fetch("/api/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                imported_reviews: importedReviewsData,
                app_name: "导入数据集",
                app_info: { name: "导入数据集", app_id: "imported" },
            }),
        });
        const data = await resp.json();
        if (data.error) { alert(data.error); return; }
        currentTaskId = data.task_id;
        pollProgress();
    } catch (e) {
        alert("启动分析失败: " + e.message);
    }
}

// 轮询进度
function pollProgress() {
    if (progressInterval) clearInterval(progressInterval);

    progressInterval = setInterval(async () => {
        try {
            const resp = await fetch(`/api/progress/${currentTaskId}`);
            const data = await resp.json();

            // 更新日志
            const logEl = document.getElementById("progress-log");
            logEl.innerHTML = data.logs.map(log =>
                `<div class="log-entry"><span class="log-time">[${log.time}]</span>${log.message}</div>`
            ).join("");
            logEl.scrollTop = logEl.scrollHeight;

            // 更新阶段
            const stageNames = {
                idle: "准备中", data_collection: "数据收集", cleaning: "数据清洗",
                analysis: "AI 语义分析", prd_generation: "生成 PRD",
                test_generation: "生成测试用例", traceability: "可追溯性验证",
                completed: "已完成", error: "出错",
            };
            document.getElementById("current-stage").textContent = stageNames[data.stage] || data.stage;

            if (data.status === "completed") {
                clearInterval(progressInterval);
                loadResults();
            } else if (data.status === "error") {
                clearInterval(progressInterval);
                alert("分析出错: " + data.error);
            }
        } catch (e) {
            console.error("轮询失败", e);
        }
    }, 1500);
}

// 加载结果
async function loadResults() {
    try {
        const resp = await fetch(`/api/results/${currentTaskId}`);
        currentResults = await resp.json();

        document.getElementById("progress-section").classList.add("hidden");
        document.getElementById("results-section").classList.remove("hidden");

        renderOverview();
        renderStats();
        renderTopics();
        renderPRD();
        renderTestCases();
        renderTraceability();
        loadReviews();
    } catch (e) {
        alert("加载结果失败: " + e.message);
    }
}

// 渲染概览
function renderOverview() {
    const d = currentResults;
    const items = [
        { number: d.clean_stats?.final_count || 0, label: "有效评论数" },
        { number: d.distribution?.avg_rating || 0, label: "平均评分" },
        { number: d.topics?.length || 0, label: "问题主题数" },
        { number: d.prd?.total_requirements || 0, label: "产品需求数" },
        { number: d.test_cases?.total_count || 0, label: "测试用例数" },
        { number: d.traceability?.conclusion || "-", label: "追溯验证" },
    ];
    document.getElementById("overview-grid").innerHTML = items.map(item => `
        <div class="overview-item">
            <div class="number">${item.number}</div>
            <div class="label">${item.label}</div>
        </div>
    `).join("");
}

// 渲染统计
function renderStats() {
    const dist = currentResults.distribution;
    if (!dist) return;

    const total = dist.total;
    let barsHtml = "";
    for (let i = 5; i >= 1; i--) {
        const count = dist.rating_distribution[i] || 0;
        const pct = total ? (count / total * 100) : 0;
        barsHtml += `
            <div class="rating-bar">
                <span class="stars">${i}星</span>
                <div class="bar-bg"><div class="bar-fill" style="width:${pct}%"></div></div>
                <span class="count">${count}</span>
            </div>
        `;
    }

    const sent = dist.sentiment;
    document.getElementById("stats-content").innerHTML = `
        <div class="rating-bars">${barsHtml}</div>
        <div class="sentiment-row">
            <div class="sentiment-item positive">
                <div style="font-size:24px;font-weight:700">${sent.positive}</div>
                <div>正面评价 (${sent.positive_rate}%)</div>
            </div>
            <div class="sentiment-item neutral">
                <div style="font-size:24px;font-weight:700">${sent.neutral}</div>
                <div>中性评价</div>
            </div>
            <div class="sentiment-item negative">
                <div style="font-size:24px;font-weight:700">${sent.negative}</div>
                <div>负面评价 (${sent.negative_rate}%)</div>
            </div>
        </div>
        <div style="margin-top:16px;font-size:13px;color:#666">
            <strong>热门关键词：</strong>
            ${Object.entries(currentResults.keywords || {}).map(([k,v]) => `${k}(${v})`).join("、 ")}
        </div>
    `;
}

// 渲染主题
function renderTopics() {
    const topics = currentResults.topics || [];
    document.getElementById("analysis-method").textContent =
        `分析方式：${currentResults.analysis_method === "llm_driven" ? "AI 模型驱动（" + (currentResults.prd?.model_used || "") + "）" : "规则降级模式"} | ${currentResults.analysis_summary || ""}`;

    document.getElementById("topics-content").innerHTML = topics.map((t, i) => `
        <div class="topic-item">
            <div class="topic-header">
                <span class="topic-name">${i+1}. ${t.name}</span>
                <div class="topic-meta">
                    <span class="badge ${t.severity}">${t.severity === "high" ? "高严重" : t.severity === "medium" ? "中严重" : "低严重"}</span>
                    <span class="badge confidence">置信度 ${(t.confidence * 100).toFixed(0)}%</span>
                </div>
            </div>
            <div class="topic-desc">${t.description}</div>
            <div class="topic-evidence">
                关联评论：${t.actual_sample_count || t.sample_count || 0} 条 |
                矛盾反馈：${t.contradictions || "无"} |
                证据说明：${t.evidence_note || "充分"}
            </div>
        </div>
    `).join("") || "<p>未发现明显问题主题</p>";
}

// 渲染 PRD
function renderPRD() {
    const prd = currentResults.prd;
    if (!prd) return;

    document.getElementById("prd-content").innerHTML = `
        <p style="margin-bottom:16px"><strong>${prd.prd_title}</strong> — ${prd.overview}</p>
        ${prd.requirements.map(req => `
            <div class="req-item">
                <div class="req-header">
                    <span class="req-id">${req.id}</span>
                    <div class="topic-meta">
                        <span class="badge ${req.priority === 'P0' ? 'high' : req.priority === 'P1' ? 'medium' : 'low'}">${req.priority}</span>
                        <span class="badge confidence">${req.version}</span>
                        ${req.is_assumption ? '<span class="badge medium">假设性需求</span>' : ''}
                    </div>
                </div>
                <div class="req-title">${req.title}</div>
                <div class="req-body">
                    <p><strong>用户故事：</strong>${req.user_story}</p>
                    <p><strong>描述：</strong>${req.description}</p>
                    <p><strong>验收标准：</strong></p>
                    <ul>${(req.acceptance_criteria || []).map(ac => `<li>${ac}</li>`).join("")}</ul>
                </div>
                <div class="req-trace">
                    来源评论ID：${(req.source_review_ids || []).join(", ") || "无"} |
                    证据等级：${req.evidence_level} | 关联主题：${req.related_topic || "-"}
                </div>
            </div>
        `).join("")}
    `;
}

// 渲染测试用例
function renderTestCases() {
    const tc = currentResults.test_cases;
    if (!tc) return;

    const cases = tc.test_cases || [];
    document.getElementById("testcases-content").innerHTML = `
        <p style="margin-bottom:12px">共 <strong>${tc.total_count}</strong> 条测试用例（生成方式：${tc.generation_method}）</p>
        <table class="tc-table">
            <thead>
                <tr><th>用例ID</th><th>标题</th><th>关联需求</th><th>类型</th><th>优先级</th><th>预期结果</th></tr>
            </thead>
            <tbody>
                ${cases.map(c => `
                    <tr>
                        <td>${c.id}</td>
                        <td>${c.title}</td>
                        <td>${c.requirement_id}</td>
                        <td>${c.type}</td>
                        <td>${c.priority}</td>
                        <td>${(c.expected_result || "").substring(0, 40)}</td>
                    </tr>
                `).join("")}
            </tbody>
        </table>
        ${cases.slice(0, 3).map(c => `
            <div class="tc-detail">
                <strong>${c.id}：${c.title}</strong>
                <p><strong>前置条件：</strong>${c.preconditions}</p>
                <p><strong>测试步骤：</strong></p>
                <ol style="margin-left:20px">${(c.steps || []).map(s => `<li>${s}</li>`).join("")}</ol>
                <p><strong>预期结果：</strong>${c.expected_result}</p>
                <p><strong>验证问题：</strong>${c.verifies_issue}</p>
                <p><strong>来源评论：</strong>${(c.source_review_ids || []).join(", ")}</p>
            </div>
        `).join("")}
    `;
}

// 渲染可追溯性
function renderTraceability() {
    const tr = currentResults.traceability;
    if (!tr) return;

    document.getElementById("traceability-content").innerHTML = `
        <div class="trace-summary">
            <div class="trace-summary-item pass">
                <div style="font-size:24px;font-weight:700">${tr.passed}</div>
                <div>通过</div>
            </div>
            <div class="trace-summary-item warn">
                <div style="font-size:24px;font-weight:700">${tr.warnings}</div>
                <div>警告</div>
            </div>
            <div class="trace-summary-item fail">
                <div style="font-size:24px;font-weight:700">${tr.failed}</div>
                <div>失败</div>
            </div>
        </div>
        <p style="margin-bottom:16px"><strong>结论：${tr.conclusion}</strong> — ${tr.conclusion_detail}</p>
        <table class="trace-matrix">
            <thead>
                <tr><th>需求ID</th><th>需求标题</th><th>关联主题</th><th>来源评论数</th><th>测试用例数</th><th>追溯链</th></tr>
            </thead>
            <tbody>
                ${(tr.traceability_matrix || []).map(m => `
                    <tr>
                        <td>${m.requirement_id}</td>
                        <td>${m.requirement_title}</td>
                        <td>${m.related_topic}</td>
                        <td>${m.source_review_count}</td>
                        <td>${m.test_case_count}</td>
                        <td class="${m.chain_complete ? 'chain-ok' : 'chain-broken'}">${m.chain_complete ? '✓ 完整' : '✗ 缺失'}</td>
                    </tr>
                `).join("")}
            </tbody>
        </table>
    `;
}

// 加载评论列表
async function loadReviews() {
    try {
        const resp = await fetch(`/api/reviews/${currentTaskId}?page=${currentReviewPage}&per_page=20&rating=${currentRatingFilter}`);
        const data = await resp.json();

        const filters = [
            { v: "0", label: "全部" },
            { v: "1", label: "1星" }, { v: "2", label: "2星" },
            { v: "3", label: "3星" }, { v: "4", label: "4星" }, { v: "5", label: "5星" },
        ];

        document.getElementById("reviews-content").innerHTML = `
            <div class="review-filters">
                ${filters.map(f => `<button class="filter-btn ${currentRatingFilter===f.v?'active':''}" onclick="filterReviews('${f.v}')">${f.label}</button>`).join("")}
            </div>
            <p style="margin-bottom:12px;font-size:13px;color:#666">共 ${data.total} 条评论</p>
            ${data.reviews.map(r => `
                <div class="review-item">
                    <div class="review-header">
                        <span class="review-author">${r.author}</span>
                        <span class="review-rating">${'★'.repeat(r.rating)}${'☆'.repeat(5-r.rating)}</span>
                    </div>
                    ${r.title ? `<div class="review-title">${r.title}</div>` : ''}
                    <div class="review-content">${r.content}</div>
                    <div class="review-meta">ID: ${r.review_id} | 版本: ${r.version || '未知'} | 有用: ${r.vote_count}</div>
                </div>
            `).join("")}
            <div class="pagination">
                <button onclick="prevPage()" ${currentReviewPage<=1?'disabled':''}>上一页</button>
                <span>第 ${currentReviewPage} 页 / 共 ${Math.ceil(data.total/20)} 页</span>
                <button onclick="nextPage()" ${currentReviewPage>=Math.ceil(data.total/20)?'disabled':''}>下一页</button>
            </div>
        `;
    } catch (e) {
        document.getElementById("reviews-content").innerHTML = `<p style="color:red">加载评论失败: ${e.message}</p>`;
    }
}

function filterReviews(rating) {
    currentRatingFilter = rating;
    currentReviewPage = 1;
    loadReviews();
}

function prevPage() {
    if (currentReviewPage > 1) { currentReviewPage--; loadReviews(); }
}

function nextPage() {
    currentReviewPage++;
    loadReviews();
}

// 回车搜索
document.getElementById("search-input").addEventListener("keypress", e => {
    if (e.key === "Enter") searchApp();
});
