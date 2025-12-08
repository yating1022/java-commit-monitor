import os
import shutil
import tempfile
import json
from datetime import datetime, timedelta
import pandas as pd
import git

# ================= 配置 =================
REPO_URL = "https://github.com/mdlldz/java.git"
OUTPUT_DIR = "public"
JSON_FILE = os.path.join(OUTPUT_DIR, "data.json")
TEMPLATE_FILE = "index.html"
# =======================================

def fetch_commit_data(repo_url):
    temp_dir = tempfile.mkdtemp()
    print(f"🚀 正在克隆仓库 {repo_url}...")
    try:
        repo = git.Repo.clone_from(repo_url, temp_dir)
        commits_list = []
        # 只获取最近的 5000 条提交，防止数据量过大
        for commit in repo.iter_commits(max_count=5000):
            commits_list.append({
                'hash': commit.hexsha[:7],  # 短哈希
                'date': datetime.fromtimestamp(commit.committed_date),
                'message': commit.message.strip(),
                'timestamp': commit.committed_date
            })
        return pd.DataFrame(commits_list)
    finally:
        try:
            repo.close()
            shutil.rmtree(temp_dir)  # 清理临时目录
        except Exception as e:
            print(f"清理临时文件时出错: {e}")

def calculate_streak(dates):
    """计算当前连续提交天数"""
    if not dates:
        return 0
    # 去重并按日期倒序排列（最新的在前）
    dates = sorted(list(set(dates)), reverse=True)
    current_streak = 0
    today = datetime.now().date()
    
    # 如果最新的提交距离今天超过1天，说明连续提交已中断
    if dates[0] < today - timedelta(days=1):
        return 0
        
    for i in range(len(dates)):
        expected_date = dates[0] - timedelta(days=i)
        if dates[i] == expected_date:
            current_streak += 1
        else:
            break
    return current_streak

def process_to_json(df):
    df['date_dt'] = pd.to_datetime(df['date'])
    df['day_str'] = df['date_dt'].dt.date  # 提取日期（不含时间）
    df['hour'] = df['date_dt'].dt.hour     # 提取小时
    df['weekday'] = df['date_dt'].dt.weekday  # 提取星期（0=周一，6=周日）
    
    # 1. 基础统计信息
    total_commits = len(df)
    last_update = df['date_dt'].max().strftime("%Y-%m-%d %H:%M")
    unique_days = df['day_str'].unique().tolist()
    current_streak = calculate_streak(unique_days)
    
    # 2. 提交趋势图数据（按天统计）
    daily_counts = df.groupby('day_str').size().reset_index(name='count')
    daily_counts = daily_counts.sort_values('day_str')
    
    # 3. 活跃时间分布（用于热力图：星期 x 小时）
    heatmap_data = []
    grouped = df.groupby(['weekday', 'hour']).size().reset_index(name='count')
    for _, row in grouped.iterrows():
        # ECharts 热力图格式：[小时, 星期, 提交次数]
        heatmap_data.append([int(row['hour']), int(row['weekday']), int(row['count'])])

    # 4. 最近提交记录（取前10条）
    recent_commits = df.head(10)[['hash', 'message', 'date']].astype(str).to_dict(orient='records')

    # 整理最终JSON数据
    data = {
        "meta": {
            "repo": REPO_URL.split('/')[-1],
            "updated": last_update,
            "total": total_commits,
            "streak": current_streak
        },
        "trend": {
            "dates": daily_counts['day_str'].astype(str).tolist(),
            "values": daily_counts['count'].tolist()
        },
        "heatmap": heatmap_data,
        "recent": recent_commits
    }
    return data

def main():
    # 创建输出目录（如果不存在）
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    # 复制模板文件到输出目录
    if os.path.exists(TEMPLATE_FILE):
        shutil.copy(TEMPLATE_FILE, os.path.join(OUTPUT_DIR, "index.html"))
    
    # 获取提交数据并生成JSON
    df = fetch_commit_data(REPO_URL)
    if df is not None and not df.empty:
        json_data = process_to_json(df)
        with open(JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False)
        print(f"🎉 数据已生成: {JSON_FILE}")
    else:
        print("❌ 未获取到提交数据")

if __name__ == "__main__":
    main()
