// 数据加载动画处理
function showLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = `
            <div class="loading">
                <div class="loading-spinner"></div>
            </div>
        `;
    }
}

function hideLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = '';
    }
}

// 格式化日期显示（增强容错，并指定东八区时区进行日期判断）
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    try {
        // 1. 核心：创建 Date 对象。
        // 要求 Python 后端必须输出包含时区信息（如 +0800）的字符串，如："2025-12-08 20:10 +0800"
        const commitDate = new Date(dateString);
        if (isNaN(commitDate.getTime())) return dateString;

        const SHANGHAI_TZ = 'Asia/Shanghai';
        
        // 2. 获取东八区的今天日期（基准时间）
        // 创建一个表示东八区午夜的 Date 对象，用于准确计算日期间隔。
        const now = new Date();
        const todayShanghaiString = now.toLocaleDateString('zh-CN', {
            timeZone: SHANGHAI_TZ,
            year: 'numeric',
            month: 'numeric',
            day: 'numeric'
        });
        // 转化为 Date 对象，表示东八区的午夜（0点）
        const todayShanghai = new Date(todayShanghaiString);

        // 3. 将提交日期也归一化为东八区的午夜（用于日期比较）
        const commitDateShanghaiString = commitDate.toLocaleDateString('zh-CN', {
            timeZone: SHANGHAI_TZ,
            year: 'numeric',
            month: 'numeric',
            day: 'numeric'
        });
        const commitDateShanghai = new Date(commitDateShanghaiString);

        // 4. 计算日期差（基于东八区午夜的时间戳）
        const diffTime = todayShanghai.getTime() - commitDateShanghai.getTime();
        // Math.round 用于处理夏令时边界或浏览器精度问题，确保得到整数天数。
        const diffDays = Math.round(diffTime / (1000 * 60 * 60 * 24)); 
        
        // 5. 格式化时间部分
        const timePart = commitDate.toLocaleTimeString('zh-CN', { 
            timeZone: SHANGHAI_TZ, 
            hour: '2-digit', 
            minute: '2-digit', 
            hour12: false // 使用 24 小时制
        });

        if (diffDays === 0) {
            return `今天 ${timePart}`;
        } else if (diffDays === 1) {
            return `昨天 ${timePart}`;
        } else if (diffDays > 1 && diffDays < 7) {
            return `${diffDays}天前`;
        } else {
            // 完整日期部分
            return commitDate.toLocaleDateString('zh-CN', {
                timeZone: SHANGHAI_TZ,
                year: 'numeric',
                month: '2-digit',
                day: '2-digit'
            }).replace(/\//g, '-'); // 将斜杠替换为横杠
        }
    } catch (e) {
        console.error("FormatDate Error:", e);
        return dateString;
    }
}

// 主函数
function initDashboard(data) {
    // === 1. 基础信息填充 (增加 || 0 保护防止报错) ===
    const meta = data.meta || {};
    
    const repoNameEl = document.getElementById('repo-name');
    if (repoNameEl) repoNameEl.innerText = `刘顺杰的JAVA学习情况`;
    
    document.getElementById('total-commits').innerText = meta.total || 0;
    document.getElementById('current-streak').innerText = meta.streak || 0;
    document.getElementById('last-study-time').innerText = formatDate(meta.updated);
    
    // [关键修复] 如果后端没有 total_lines，默认用 0，防止 .toLocaleString() 报错
    const totalLines = meta.total_lines || 0;
    document.getElementById('total-lines').innerText = totalLines.toLocaleString();

    // === 2. 渲染最近提交列表 ===
    const listEl = document.getElementById('commit-list');
    hideLoading('commit-list');
    
    const recentCommits = Array.isArray(data.recent) ? data.recent : [];
    
    if (recentCommits.length === 0) {
        if(listEl) listEl.innerHTML = '<div style="text-align:center; padding:10px; color:#999">暂无记录</div>';
    } else {
        if(listEl) {
            recentCommits.forEach(commit => {
                const li = document.createElement('li');
                li.className = 'commit-item';
                
                // [关键修复] 防止 lines 为空
                const linesCount = (commit.lines || 0).toLocaleString();
                const hash = commit.hash || '???';
                const msg = commit.message || '无描述';

                li.innerHTML = `
                    <div class="commit-hash">${hash}</div>
                    <div class="commit-info">
                        <div class="commit-msg">${msg}</div>
                        <div class="commit-details">
                            <div><i class="fa-solid fa-clock"></i> ${formatDate(commit.date)}</div>
                            <div><i class="fa-solid fa-code"></i> ${linesCount} 行代码</div>
                        </div>
                    </div>
                `;
                listEl.appendChild(li);
            });
        }
    }

    // === 3. ECharts 图表渲染 (代码保持不变) ===
    const commonOption = {
        textStyle: { fontFamily: 'Inter, sans-serif' },
        tooltip: { 
            trigger: 'axis', 
            backgroundColor: 'rgba(255, 255, 255, 0.9)', 
            borderColor: '#e2e8f0',
            borderWidth: 1,
            textStyle: { color: '#1e293b' },
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.05)'
        },
        grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true }
    };

    // --- 趋势图 ---
    hideLoading('trendChart');
    const trendChartDom = document.getElementById('trendChart');
    if (trendChartDom) {
        const trendChart = echarts.init(trendChartDom);
        const trendData = data.trend || { dates: [], values: [] };
        
        trendChart.setOption({
            ...commonOption,
            animationDuration: 1500,
            xAxis: { 
                type: 'category', 
                data: trendData.dates || [],
                axisLine: { lineStyle: { color: '#cbd5e1' } },
                axisLabel: { color: '#64748b', rotate: 30 }
            },
            yAxis: { 
                type: 'value', 
                name: '提交次数',
                splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } }
            },
            series: [{
                data: trendData.values || [],
                type: 'line',
                smooth: true,
                symbol: 'circle',
                symbolSize: 6,
                // [修复] 不能用 var(--accent)，改为具体颜色
                itemStyle: { color: '#3b82f6' }, 
                lineStyle: { width: 3, color: '#3b82f6' },
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: 'rgba(59, 130, 246, 0.2)' },
                        { offset: 1, color: 'rgba(59, 130, 246, 0.01)' }
                    ])
                }
            }]
        });
        window.addEventListener('resize', () => trendChart.resize());
    }

    // --- 热力图 ---
    hideLoading('heatmapChart');
    const heatmapChartDom = document.getElementById('heatmapChart');
    if (heatmapChartDom) {
        const heatmapChart = echarts.init(heatmapChartDom);
        const days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
        const hours = Array.from({length: 24}, (_, i) => `${i}时`);
        const heatmapData = data.heatmap || [];
        
        // 计算最大值用于颜色映射
        let maxVal = 5;
        if(heatmapData.length > 0) {
             maxVal = Math.max(...heatmapData.map(i => i[2])) || 5;
        }

        heatmapChart.setOption({
            animationDuration: 1500,
            tooltip: { position: 'top' },
            grid: { height: '80%', top: '5%', bottom: '15%' },
            xAxis: { type: 'category', data: hours, splitArea: { show: true } },
            yAxis: { type: 'category', data: days, splitArea: { show: true } },
            visualMap: {
                min: 0, max: maxVal, calculable: false, orient: 'horizontal',
                left: 'center', bottom: '0%',
                inRange: { color: ['#eff6ff', '#dbeafe', '#bfdbfe', '#93c5fd'] }
            },
            series: [{
                type: 'heatmap',
                data: heatmapData,
                itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 1 }
            }]
        });
        window.addEventListener('resize', () => heatmapChart.resize());
    }

    // 触发 resize 修复初次渲染宽度问题
    setTimeout(() => window.dispatchEvent(new Event('resize')), 100);
}

// 启动入口
// 检查元素是否存在，防止报错
if(document.getElementById('commit-list')) showLoading('commit-list');
if(document.getElementById('trendChart')) showLoading('trendChart');
if(document.getElementById('heatmapChart')) showLoading('heatmapChart');

fetch('data.json')
    .then(res => {
        if(!res.ok) throw new Error("HTTP error " + res.status);
        return res.json();
    })
    .then(data => {
        initDashboard(data);
    })
    .catch(err => {
        console.error("数据加载失败:", err);
        const repoName = document.getElementById('repo-name');
        if(repoName) repoName.innerText = "数据加载失败";
        
        hideLoading('commit-list');
        hideLoading('trendChart');
        hideLoading('heatmapChart');
        
        const listEl = document.getElementById('commit-list');
        if(listEl) listEl.innerHTML = `<div style="color:red;text-align:center;padding:20px">加载失败，请检查控制台</div>`;
    });
