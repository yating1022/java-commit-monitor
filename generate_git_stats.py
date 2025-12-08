import os
import shutil
import tempfile
import json
from datetime import datetime
import pandas as pd
import git

# =================配置区域=================
REPO_URL = "https://github.com/mdlldz/java.git"
OUTPUT_DIR = "public"
JSON_FILE = os.path.join(OUTPUT_DIR, "data.json")
TEMPLATE_FILE = "index.html" # 根目录下的静态模板
# =========================================

def fetch_commit_data(repo_url):
    temp_dir = tempfile.mkdtemp()
    print(f"🚀 正在克隆仓库 {repo_url}...")
    try:
        repo = git.Repo.clone_from(repo_url, temp_dir)
        commits_list = []
        for commit in repo.iter_commits():
            commits_list.append({
                'author': commit.author.name,
                'date': datetime.fromtimestamp(commit.committed_date),
            })
        return pd.DataFrame(commits_list)
    finally:
        try:
            repo.close()
            shutil.rmtree(temp_dir)
        except Exception:
            pass

def process_to_json(df):
    """将 DataFrame 处理为纯 JSON 结构"""
    df['date'] = pd.to_datetime(df['date'])
    df['day_str'] = df['date'].dt.date.astype(str) # 转字符串以便JSON序列化
    df['hour'] = df['date'].dt.hour
    df['weekday'] = df['date'].dt.day_name()
    
    # 1. 趋势数据
    daily_counts = df.groupby('day_str').size().reset_index(name='count')
    daily_counts = daily_counts.sort_values('day_str') # 确保时间顺序
    
    # 2. 热力图数据
    week_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    heatmap_data = df.groupby(['weekday', 'hour'], observed=False).size().reset_index(name='count')
    # 为了方便前端 Plotly 处理，我们这里需要构造矩阵，或者直接给 xyz 列表
    # 这里我们直接给 xyz 列表，让前端处理
    
    # 3. 作者数据
    author_counts = df['author'].value_counts().reset_index().head(10)
    author_counts.columns = ['author', 'count']

    # 构造最终 JSON 字典
    data = {
        "repo_name": REPO_URL.split('/')[-1],
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "trend": {
            "dates": daily_counts['day_str'].tolist(),
            "counts": daily_counts['count'].tolist()
        },
        "heatmap": {
            "weekdays": heatmap_data['weekday'].tolist(),
            "hours": heatmap_data['hour'].tolist(),
            "counts": heatmap_data['count'].tolist()
        },
        "authors": {
            "names": author_counts['author'].tolist(),
            "counts": author_counts['count'].tolist()
        }
    }
    return data

def main():
    # 1. 准备输出目录
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    # 2. 复制静态 HTML 模板到 public 目录
    if os.path.exists(TEMPLATE_FILE):
        shutil.copy(TEMPLATE_FILE, os.path.join(OUTPUT_DIR, "index.html"))
        print("✅ 已将模板 index.html 复制到 public 目录")
    else:
        print("⚠️ 警告：根目录下没找到 index.html 模板！")

    # 3. 抓取与生成数据
    df = fetch_commit_data(REPO_URL)
    if df is not None and not df.empty:
        json_data = process_to_json(df)
        
        with open(JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False)
            
        print(f"🎉 成功生成数据文件: {JSON_FILE}")
    else:
        print("❌ 未获取到数据")

if __name__ == "__main__":
    main()
    print("✅ 脚本运行结束")
