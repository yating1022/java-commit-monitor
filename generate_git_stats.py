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
        
        # 获取最近的 2000 条提交
        print("📊 正在分析提交数据 (这可能需要几分钟)...")
        for commit in repo.iter_commits(max_count=2000):
            try:
                # 获取代码行数变动
                stats = commit.stats.total
                lines_changed = stats.get('lines', 0)
            except:
                lines_changed = 0

            commits_list.append({
                'hash': commit.hexsha[:7],
                'date': datetime.fromtimestamp(commit.committed_date),
                'message': commit.message.strip(),
                'timestamp': commit.committed_date,
                'lines': lines_changed
            })
        return pd.DataFrame(commits_list)
    finally:
        try:
            repo.close()
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"清理临时文件时出错: {e}")

def calculate_streak(dates):
    if not dates:
        return 0
    dates = sorted(list(set(dates)), reverse=True)
    current_streak = 0
    today = datetime.now().date()
    
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
    df['weekday'] = df['date_dt'].dt.weekday
    
    total_commits = len(df)
    total_lines = int(df['lines'].sum())
    last_update = df['date_dt'].max().strftime("%Y-%m-%d %H:%M")
    unique_days = df['day_str'].unique().tolist()
    current_streak = calculate_streak(unique_days)
    
    daily_counts = df.groupby('day_str').size().reset_index(name='count')
    daily_counts = daily_counts.sort_values('day_str')
    
    heatmap_data = []
    grouped = df.groupby(['weekday', 'hour']).size().reset_index(name='count')
    for _, row in grouped.iterrows():
        heatmap_data.append([int(row['hour']), int(row['weekday']), int(row['count'])])

    recent_commits = df.head(10)[['hash', 'message', 'date', 'lines']].copy()
    recent_commits['date'] = recent_commits['date'].astype(str)
    recent_records = recent_commits.to_dict(orient='records')

    data = {
        "meta": {
            "repo": REPO_URL.split('/')[-1].replace('.git', ''),
            "updated": last_update,
            "total": total_commits,
            "streak": current_streak,
            "total_lines": total_lines
        },
        "trend": {
            "dates": daily_counts['day_str'].astype(str).tolist(),
            "values": daily_counts['count'].tolist()
        },
        "heatmap": heatmap_data,
        "recent": recent_records
    }
    return data

def main():
    # 1. 准备输出目录
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    # 2. 复制静态资源 (增加防错逻辑)
    resources = [
        (TEMPLATE_FILE, "index.html"),
        ("public/style.css", "style.css"),
        ("public/script.js", "script.js")
    ]
    
    for src, dst_name in resources:
        # 如果源文件找不到，尝试在根目录找（兼容性处理）
        if not os.path.exists(src) and os.path.exists(os.path.basename(src)):
            src = os.path.basename(src)
            
        if os.path.exists(src):
            dst_path = os.path.join(OUTPUT_DIR, dst_name)
            
            # [核心修复] 检查源文件和目标文件是否相同
            # 如果是同一个文件（例如都是 public/style.css），直接跳过，不复制
            if os.path.abspath(src) == os.path.abspath(dst_path):
                print(f"ℹ️ 跳过复制 (原地文件): {src}")
                continue
                
            shutil.copy(src, dst_path)
            print(f"✅ 已复制资源: {src} -> {dst_name}")
        else:
            print(f"⚠️ 警告: 找不到资源文件 {src}")

    # 3. 获取数据并生成 JSON
    df = fetch_commit_data(REPO_URL)
    if df is not None and not df.empty:
        json_data = process_to_json(df)
        with open(JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False)
        print(f"🎉 数据生成成功: {JSON_FILE}")
    else:
        print("❌ 未能获取数据")

if __name__ == "__main__":
    main()
