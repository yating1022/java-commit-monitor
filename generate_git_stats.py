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
        # 只要最近的 5000 条，防止数据量过大卡顿
        for commit in repo.iter_commits(max_count=5000):
            commits_list.append({
                'hash': commit.hexsha[:7], # 短 hash
                'date': datetime.fromtimestamp(commit.committed_date),
                'message': commit.message.strip(),
                'timestamp': commit.committed_date
            })
        return pd.DataFrame(commits_list)
    finally:
        try:
            repo.close()
            shutil.rmtree(temp_dir)
        except Exception:
            pass

def calculate_streak(dates):
    """计算当前连续提交天数"""
    if not dates:
        return 0
    dates = sorted(list(set(dates)), reverse=True) # 从大到小排
    current_streak = 0
    today = datetime.now().date()
    
    # 如果最新的提交不是今天或昨天，说明断了
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
    df['day_str'] = df['date_dt'].dt.date
    df['hour'] = df['date_dt'].dt.hour
    df['weekday'] = df['date_dt'].dt.weekday # 0=Mon, 6=Sun
    
    # 1. 基础统计
    total_commits = len(df)
    last_update = df['date_dt'].max().strftime("%Y-%m-%d %H:%M")
    unique_days = df['day_str'].unique().tolist()
    current_streak = calculate_streak(unique_days)
    
    # 2. 趋势图 (按天)
    daily_counts = df.groupby('day_str').size().reset_index(name='count')
    daily_counts = daily_counts.sort_values('day_str')
    
    # 3. 活跃时间分布 (周 x 小时) - 用于热力图
    heatmap_data = []
    grouped = df.groupby(['weekday', 'hour']).size().reset_index(name='count')
    for _, row in grouped.iterrows():
        # ECharts heatmap 格式: [x, y, value] -> [hour, weekday, count]
        heatmap_data.append([int(row['hour']), int(row['weekday']), int(row['count'])])

    # 4. 最近提交记录 (取前 10 条)
    recent_commits = df.head(10)[['hash', 'message', 'date']].astype(str).to_dict(orient='records')

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
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    if os.path.exists(TEMPLATE_FILE):
        shutil.copy(TEMPLATE_FILE, os.path.join(OUTPUT_DIR, "index.html"))
    
    df = fetch_commit_data(REPO_URL)
    if df is not None and not df.empty:
        json_data = process_to_json(df)
        with open(JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False)
        print(f"🎉 数据已生成: {JSON_FILE}")
    else:
        print("❌ 无数据")

if __name__ == "__main__":
    main()
