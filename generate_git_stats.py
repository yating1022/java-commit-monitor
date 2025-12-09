import os
import shutil
import tempfile
import json
from datetime import datetime, timedelta, timezone
import pandas as pd
import git
import pytz # 确保已安装: pip install pytz

# ================= 配置 =================
REPO_URL = "https://github.com/mdlldz/java.git"
OUTPUT_DIR = "public"
JSON_FILE = os.path.join(OUTPUT_DIR, "data.json")
TEMPLATE_FILE = "index.html"
SHANGHAI_TZ = 'Asia/Shanghai' # 定义东八区时区
# =======================================

def fetch_commit_data(repo_url):
    """克隆仓库并获取提交数据。"""
    temp_dir = tempfile.mkdtemp()
    print(f"🚀 正在克隆仓库 {repo_url}...")
    try:
        repo = git.Repo.clone_from(repo_url, temp_dir) 
        commits_list = []
        
        print("📊 正在分析提交数据 (这可能需要几分钟)...")
        for commit in repo.iter_commits(max_count=2000):
            try:
                stats = commit.stats.total
                lines_changed = stats.get('lines', 0)
            except Exception:
                lines_changed = 0

            # 保持 'date' 列为 naive datetime 对象，后续再进行时区标记和转换。
            commits_list.append({
                'hash': commit.hexsha[:7],
                'date': datetime.fromtimestamp(commit.committed_date), 
                'message': commit.message.strip(),
                'timestamp': commit.committed_date,
                'lines': lines_changed
            })
        return pd.DataFrame(commits_list)
    except Exception as e:
        print(f"❌ 克隆或分析仓库时出错: {e}")
        return None
    finally:
        try:
            if 'repo' in locals() and repo:
                repo.close()
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"清理临时文件时出错: {e}")

def calculate_streak(dates):
    """
    计算连续提交天数（基于东八区时间）。
    此版本逻辑更简洁和健壮。
    """
    if not dates:
        return 0
    
    # 1. 确定今天的日期（东八区）
    try:
        tz = pytz.timezone(SHANGHAI_TZ)
    except pytz.UnknownTimeZoneError:
        tz = timezone.utc
        
    now_shanghai = datetime.now(tz)
    today = now_shanghai.date()
    
    # 2. 获取唯一的提交日期集合
    dates_set = set(d.date() if isinstance(d, datetime) else d for d in dates)
    
    if not dates_set:
        return 0
        
    # 3. 检查连击是否中断
    # 找到最新的提交日期
    latest_commit_date = max(dates_set) 
    
    # 如果最新提交日期早于“昨天”，则连击为 0
    if latest_commit_date < today - timedelta(days=1):
        return 0
        
    current_streak = 0
    
    # 4. 从今天开始倒推检查连续性
    check_date = today
    
    # 从今天或昨天开始计算
    # 如果今天有提交，从今天开始
    if check_date in dates_set:
        current_streak += 1
        check_date -= timedelta(days=1)
    # 如果今天没有提交，但昨天有提交，连击从昨天开始（连击长度为 1）
    elif check_date - timedelta(days=1) in dates_set:
        current_streak += 1
        check_date -= timedelta(days=2) # 从前天开始继续检查
    else:
        return 0 # 今天和昨天都没有，连击中断

    # 5. 持续往前检查
    while check_date in dates_set:
        current_streak += 1
        check_date -= timedelta(days=1)
        
    return current_streak

def process_to_json(df):
    """数据处理与结构化，直接在现有列上进行东八区时区转换。"""
    
    # 1. 时区转换
    # 'date' 列是 naive datetime，首先假设它是 UTC 时间进行本地化
    df['date'] = pd.to_datetime(df['date']).dt.tz_localize('UTC', ambiguous='NaT', nonexistent='shift_forward')
    
    # 将其转换为东八区时间 (Asia/Shanghai) 并覆盖原始列
    df['date'] = df['date'].dt.tz_convert(SHANGHAI_TZ)
    
    # 2. 提取统计所需的列（临时使用，不创建持久新列）
    df['day_str'] = df['date'].dt.date
    df['hour'] = df['date'].dt.hour
    df['weekday'] = df['date'].dt.weekday # [0=周一, 6=周日]
    
    # 3. 计算元数据
    total_commits = len(df)
    total_lines = int(df['lines'].sum())
    # last_update 使用东八区时间格式化，显示最新的提交时间
    last_update = df['date'].max().strftime("%Y-%m-%d %H:%M") 
    
    unique_days = df['day_str'].unique().tolist()
    current_streak = calculate_streak(unique_days)
    
    # 4. 趋势图数据 (Trend)
    daily_counts = df.groupby('day_str').size().reset_index(name='count')
    daily_counts = daily_counts.sort_values('day_str')
    
    # 5. 热力图数据 (Heatmap)
    heatmap_data = []
    grouped = df.groupby(['weekday', 'hour']).size().reset_index(name='count') 
    for _, row in grouped.iterrows():
        heatmap_data.append([int(row['hour']), int(row['weekday']), int(row['count'])])

    # 6. 最近提交 (Recent)
    # 确保 'date' 已经被转换为东八区时间
    recent_commits = df.head(10)[['hash', 'message', 'date', 'lines']].copy()
    # 使用东八区时间进行格式化
    recent_commits['date'] = recent_commits['date'].dt.strftime("%Y-%m-%d %H:%M:%S %Z")
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
    """主函数。"""
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
        # 兼容性处理：如果找不到，尝试在根目录找
        if not os.path.exists(src) and os.path.exists(os.path.basename(src)):
            src = os.path.basename(src)
            
        if os.path.exists(src):
            dst_path = os.path.join(OUTPUT_DIR, dst_name)
            
            # 避免复制到自身
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
            json.dump(json_data, f, ensure_ascii=False, indent=4) 
        print(f"🎉 数据生成成功: {JSON_FILE}")
    else:
        print("❌ 未能获取数据或数据为空")

if __name__ == "__main__":
    main()
