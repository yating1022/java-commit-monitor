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

// 格式化日期显示
function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now - date);
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) {
        return `今天 ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
    } else if (diffDays === 1) {
        return `昨天 ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
    } else if (diffDays < 7) {
        return `${diffDays}天前`;
    } else {
        return `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}-${date.getDate().toString().padStart(2, '0')}`;
    }
}

// 主函数
function initDashboard(data) {
    // 1. 填充基础文本
    const repoNameEl = document.getElementById('repo-name');
    if (repoNameEl) repoNameEl.innerText = `${data.meta.repo} 学习进度`;
    
    document.getElementById('total-commits').innerText = data.meta.total;
    document.getElementById('current-streak').innerText = data.meta.streak;
    document.getElementById('last-study-time').innerText = formatDate(data.meta.updated);
    document.getElementById('total-lines').innerText = data.meta.total_lines.toLocaleString();

    // 2. 渲染最近提交列表
    const listEl = document.getElementById('commit-list');
    hideLoading('commit-list');
    
    data.recent.forEach(commit => {
        const li = document.createElement('li');
        li.className = 'commit-item';
        li.innerHTML = `
            <div class="commit-hash">${commit.hash}</div>
            <div class="commit-info">
                <div class="commit-msg">${commit.message}</div>
                <div class="commit-details">
                    <div><i class="fa-solid fa-clock"></i> ${formatDate(commit.date)}</div>
                    <div><i class="fa-solid fa-code"></i> ${commit.lines.toLocaleString()} 行代码</div>
                </div>
            </div>
        `;
        listEl.appendChild(li);
    });

    // 3. ECharts 通用配置
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
        
        // 为趋势图添加渐入动画
        trendChart.setOption({
            ...commonOption,
            animationDuration: 1500,
            xAxis: { 
                type: 'category', 
                data: data.trend.dates,
                axisLine: { lineStyle: { color: '#cbd5e1' } },
                axisLabel: { 
                    color: '#64748b',
                    rotate: 30,
                    interval: 'auto'
                }
            },
            yAxis: { 
                type: 'value', 
                name: '学习次数',
                nameTextStyle: { color: '#64748b' },
                splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } },
                axisLabel: { color: '#64748b' }
            },
            series: [{
                data: data.trend.values,
                type: 'line',
                smooth: true,
                symbol: 'circle',
                symbolSize: 6,
                // [修复点] 这里原来写的是 var(--accent)，这是 CSS 语法，JS 会报错。
                // 已修改为具体的蓝色值 '#3b82f6'
                itemStyle: { color: '#3b82f6' }, 
                lineStyle: { width: 3, color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                    {offset: 0, color: '#3b82f6'}, 
                    {offset: 1, color: '#60a5fa'}
                ]) },
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: 'rgba(59, 130, 246, 0.2)' },
                        { offset: 1, color: 'rgba(59, 130, 246, 0.01)' }
                    ])
                },
                emphasis: {
                    scale: true,
                    itemStyle: { shadowBlur: 10, shadowColor: 'rgba(59, 130, 246, 0.5)' }
                }
            }]
        });

        // 响应式调整 (trendChart scope)
        window.addEventListener('resize', () => {
            trendChart.resize();
        });
    }

    // --- 热力图 ---
    hideLoading('heatmapChart');
    const heatmapChartDom = document.getElementById('heatmapChart');
    if (heatmapChartDom) {
        const heatmapChart = echarts.init(heatmapChartDom);
        const days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
        const hours = Array.from({length: 24}, (_, i) => `${i}时`);
        
        heatmapChart.setOption({
            animationDuration: 1500,
            tooltip: { 
                position: 'top',
                formatter: function(params) {
                    return `${days[params.data[1]]} ${hours[params.data[0]]}<br>学习次数: ${params.data[2]}`;
                }
            },
            grid: { height: '80%', top: '5%', bottom: '15%' },
            xAxis: { 
                type: 'category', 
                data: hours, 
                splitArea: { show: true, areaStyle: { color: ['#f8fafc', '#f1f5f9'] } },
                axisLabel: { color: '#64748b', interval: 1 }
            },
            yAxis: { 
                type: 'category', 
                data: days, 
                splitArea: { show: true, areaStyle: { color: ['#f8fafc', '#f1f5f9'] } },
                axisLabel: { color: '#64748b' }
            },
            visualMap: {
                min: 0,
                max: Math.max(...data.heatmap.map(i => i[2])) || 5,
                calculable: false,
                orient: 'horizontal',
                left: 'center',
                bottom: '0%',
                inRange: { color: ['#eff6ff', '#dbeafe', '#bfdbfe', '#93c5fd'] },
                textStyle: { color: '#64748b' }
            },
            series: [{
                type: 'heatmap',
                data: data.heatmap,
                label: { show: false },
                itemStyle: { 
                    borderRadius: 4,
                    borderColor: '#f8fafc',
                    borderWidth: 1
                }
            }]
        });

         // 响应式调整 (heatmapChart scope)
         window.addEventListener('resize', () => {
            heatmapChart.resize();
        });
    }

    // 初始加载时触发一次 resize 确保图表正确显示
    setTimeout(() => {
        window.dispatchEvent(new Event('resize'));
    }, 100);
}

// 加载数据
// 确保 DOM 元素存在再调用 showLoading，防止报错
if(document.getElementById('commit-list')) showLoading('commit-list');
if(document.getElementById('trendChart')) showLoading('trendChart');
if(document.getElementById('heatmapChart')) showLoading('heatmapChart');

fetch('data.json')
    .then(response => {
        if (!response.ok) throw new Error('数据加载失败');
        return response.json();
    })
    .then(data => {
        initDashboard(data);
    })
    .catch(err => {
        console.error(err);
        const repoName = document.getElementById('repo-name');
        if(repoName) repoName.innerText = "数据加载失败";
        
        // 隐藏所有加载动画
        hideLoading('commit-list');
        hideLoading('trendChart');
        hideLoading('heatmapChart');
        
        // 显示错误信息
        const listEl = document.getElementById('commit-list');
        if (listEl) {
            const errorMsg = document.createElement('div');
            errorMsg.style.textAlign = 'center';
            errorMsg.style.padding = '20px';
            errorMsg.style.color = '#dc2626';
            errorMsg.innerHTML = '<i class="fa-solid fa-exclamation-circle"></i> 无法加载学习数据，请稍后重试';
            listEl.appendChild(errorMsg);
        }
    });
