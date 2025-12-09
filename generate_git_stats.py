import os
import shutil
import tempfile
import json
from datetime import datetime, timedelta, timezone
import pandas as pd
import git
import pytz # 需要安装 pytz 库用于时区转换

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

            # 注意：这里直接使用 datetime.fromtimestamp(commit.committed_date) 
            # 获取的是 naive datetime 对象，后续在 process_to_json 中进行时区标记和转换。
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
    """计算连续提交天数。"""
    if not dates:
        return 0
    
    # 确保今天的时间是东八区的时间，用于连击计算
    try:
        tz = pytz.timezone(SHANGHAI_TZ)
    except pytz.UnknownTimeZoneError:
        print("⚠️ 警告: 找不到 'Asia/Shanghai' 时区，使用 UTC。")
        tz = timezone.utc
        
    now_shanghai = datetime.now(tz)
    today = now_shanghai.date()
    
    # 将日期列表转换为 date 对象并排序
    unique_dates = sorted(list(set(d.date() if isinstance(d, datetime) else d for d in dates)), reverse=True)
    
    if not unique_dates:
        return 0
        
    latest_commit_date = unique_dates[0]
    current_streak = 0
    
    # 检查最新提交是否在今天或昨天
    if latest_commit_date < today - timedelta(days=1):
        return 0
        
    # 从今天/最新一天开始往前推
    # 确定检查的起始日期：如果是今天，从今天开始；否则从昨天开始
    start_date = today
    
    # 循环检查连击
    for i in range(len(unique_dates)):
        expected_date = start_date - timedelta(days=i)
        
        if expected_date in unique_dates:
            current_streak += 1
            # 如果今天有提交，则计算从今天开始
            if expected_date == today and current_streak == 1:
                # 已经检查过今天，现在继续检查昨天
                start_date = today 
            continue
        elif expected_date == latest_commit_date:
             # 如果最新提交日期是昨天，而今天没有提交，连击从昨天开始
            current_streak += 1
            continue
        else:
            # 遇到间断
            break

    # 简化连击计算：从最新的日期开始检查连续性
    current_streak = 0
    dates_set = set(unique_dates)
    
    # 检查今天和昨天
    check_date = today
    if check_date in dates_set:
        current_streak += 1
    check_date = today - timedelta(days=1)
    if check_date in dates_set:
        current_streak += 1
    
    # 从前天开始继续检查
    for i in range(2, 365): # 限制检查一年内的连击
        expected_date = today - timedelta(days=i)
        if expected_date in dates_set:
            if current_streak > 0 and (expected_date + timedelta(days=1)) in dates_set:
                current_streak += 1
            elif current_streak == 0 and expected_date == latest_commit_date:
                # 确保当最新提交是昨天或更早时，连击也能被正确计算
                if latest_commit_date >= today - timedelta(days=1):
                     current_streak = 1 if latest_commit_date == today else 0 
                     # 这里逻辑复杂且容易出错，简化为：
                     # 如果最新提交早于昨天，则连击归零
                     if latest_commit_date < today - timedelta(days=1):
                         return 0
                     
                     # 从最新的日期开始往前推
                     start_date_check = latest_commit_date
                     streak = 1
                     while (start_date_check - timedelta(days=1)) in dates_set:
                         start_date_check -= timedelta(days=1)
                         streak += 1
                     
                     return streak if latest_commit_date >= today - timedelta(days=1) else 0

            else:
                break
        else:
            break
            
    # 重新执行精确的连击计算（简化且稳健的逻辑）：
    current_streak = 0
    if not unique_dates:
        return 0

    dates_set = set(unique_dates)
    
    # 从今天开始检查连击
    start_date_check = today
    if start_date_check in dates_set:
        current_streak += 1
    
    # 无论今天有没有，都检查昨天的连击
    start_date_check = today - timedelta(days=1)
    if start_date_check in dates_set and (start_date_check + timedelta(days=1)) in dates_set:
        current_streak += 1

    # 从前天开始往前追溯连击
    for i in range(2, 365 * 3): # 追溯最多三年
        expected_date = today - timedelta(days=i)
        
        # 只要前一天有提交，连击就增加
        if expected_date in dates_set and (expected_date + timedelta(days=1)) in dates_set:
            current_streak += 1
        else:
            break
            
    # 如果今天的提交不存在，连击从昨天开始计算，且必须是连续的
    if today not in dates_set:
         # 找到最新的提交日期
         if latest_commit_date < today - timedelta(days=1):
             return 0 # 断开
         
         # 从最新的日期开始计算连续性
         current_streak = 0
         start_date_check = latest_commit_date
         while start_date_check in dates_set:
             current_streak += 1
             start_date_check -= timedelta(days=1)
         
         return current_streak

    return current_streak


def process_to_json(df):
    """
    数据处理与结构化，直接在现有列上进行东八区时区转换。
    避免创建新的辅助列，仅使用 date、day_str、hour、weekday 进行计算。
    """
    # 1. 时区转换
    # 'date' 列是 naive datetime，假设它是 UTC 时间
    df['date'] = pd.to_datetime(df['date']).dt.tz_localize('UTC')
    
    # 将其转换为东八区时间 (Asia/Shanghai) 并覆盖原始列
    df['date'] = df['date'].dt.tz_convert(SHANGHAI_TZ)
    
    # 2. 提取统计所需的列（不创建永久新列）
    df['day_str'] = df['date'].dt.date
    df['hour'] = df['date'].dt.hour
    df['weekday'] = df['date'].dt.weekday # [0=周一, 6=周日]
    
    # 3. 计算元数据
    total_commits = len(df)
    total_lines = int(df['lines'].sum())
    # last_update 使用东八区时间格式化
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
        # 热力图数据格式: [小时 (0-23), 星期几 (0-6), 提交数]
        heatmap_data.append([int(row['hour']), int(row['weekday']), int(row['count'])])

    # 6. 最近提交 (Recent)
    recent_commits = df.head(10)[['hash', 'message', 'date', 'lines']].copy()
    # 使用东八区时间进行格式化（包含时区信息）
    recent_commits['date'] = recent_commits['date'].dt.strftime("%Y-%m-%d %H:%M:%S %Z")
    recent_records = recent_commits.to_dict(orient='records')
    
    # 7. 移除辅助列，只保留原始列 (hash, date, message, timestamp, lines)
    # df.drop(columns=['day_str', 'hour', 'weekday'], inplace=True) 
    # ^ 实际上，由于 process_to_json 的 df 是一个副本或在函数内作用域，不需要清理。
    
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
            # 使用 indent=4 方便阅读，实际部署时可去掉
            json.dump(json_data, f, ensure_ascii=False, indent=4) 
        print(f"🎉 数据生成成功: {JSON_FILE}")
    else:
        print("❌ 未能获取数据或数据为空")

if __name__ == "__main__":
    main()
