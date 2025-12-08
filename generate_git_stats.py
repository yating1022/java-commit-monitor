import os
import shutil
import tempfile
from datetime import datetime
import pandas as pd
import git
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

# =================配置区域=================
REPO_URL = "https://github.com/mdlldz/java.git"
OUTPUT_DIR = "public"  # 输出目录
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "index.html") # 命名为 index.html 以便默认访问
# =========================================

def fetch_commit_data(repo_url):
    temp_dir = tempfile.mkdtemp()
    print(f"🚀 正在克隆仓库 {repo_url}...")
    try:
        repo = git.Repo.clone_from(repo_url, temp_dir)
        commits_list = []
        for commit in repo.iter_commits():
            commits_list.append({
                'hash': commit.hexsha,
                'author': commit.author.name,
                'date': datetime.fromtimestamp(commit.committed_date),
                'message': commit.message.strip()
            })
        return pd.DataFrame(commits_list)
    finally:
        try:
            repo.close()
            shutil.rmtree(temp_dir)
        except Exception:
            pass

def process_data(df):
    df['date'] = pd.to_datetime(df['date'])
    df['day_str'] = df['date'].dt.date
    df['hour'] = df['date'].dt.hour
    df['weekday'] = df['date'].dt.day_name()
    week_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    df['weekday'] = pd.Categorical(df['weekday'], categories=week_order, ordered=True)
    return df

def generate_visuals(df):
    daily_counts = df.groupby('day_str').size().reset_index(name='count')
    heatmap_data = df.groupby(['weekday', 'hour']).size().reset_index(name='count')
    author_counts = df['author'].value_counts().reset_index().head(10)
    author_counts.columns = ['author', 'count']

    fig = make_subplots(
        rows=3, cols=2,
        column_widths=[0.7, 0.3],
        row_heights=[0.5, 0.25, 0.25],
        specs=[[{"colspan": 2}, None], [{"rowspan": 2}, {}], [None, {}]],
        subplot_titles=("📈 Commit 趋势 (UTC时间)", "🔥 活跃热力图", "🏆 贡献者 Top 10", "")
    )

    fig.add_trace(go.Scatter(x=daily_counts['day_str'], y=daily_counts['count'], mode='lines', fill='tozeroy', name='提交数', line=dict(color='#00d2ff')), row=1, col=1)
    fig.add_trace(go.Heatmap(x=heatmap_data['hour'], y=heatmap_data['weekday'], z=heatmap_data['count'], colorscale='Viridis', name='活跃度'), row=2, col=1)
    fig.add_trace(go.Pie(labels=author_counts['author'], values=author_counts['count'], hole=.4, marker=dict(colors=px.colors.qualitative.Pastel)), row=2, col=2)

    fig.update_layout(title_text=f"Git 分析报告: {REPO_URL.split('/')[-1]}", template="plotly_dark", height=900)
    fig.update_xaxes(rangeslider_visible=True, row=1, col=1)
    return fig

def main():
    # 确保输出目录存在
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    df = fetch_commit_data(REPO_URL)
    if not df.empty:
        df = process_data(df)
        fig = generate_visuals(df)
        fig.write_html(OUTPUT_FILE)
        print(f"🎉 成功生成: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
