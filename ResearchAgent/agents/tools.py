from langchain_community.tools.tavily_search import TavilySearchResults
from core.config import TAVILY_API_KEY
from langchain_core.tools import tool

import os


# 确保环境变量里有 TAVILY_API_KEY，LangChain 底层会自动去这里找
os.environ["TAVILY_API_KEY"] = TAVILY_API_KEY

def get_web_search_tool(max_results: int = 4):
    """
    增强版全网搜索引擎
    使用 Tavily 的高级参数，强制返回包含完整内容的高质量链接
    """
    if not TAVILY_API_KEY:
        raise ValueError("TAVILY_API_KEY 未配置！请在 .env 文件中设置。")
        
    os.environ["TAVILY_API_KEY"] = TAVILY_API_KEY
    
    # 启用 advanced 模式，并尽量拉取长文本 content 
    search_tool = TavilySearchResults(
        max_results=max_results,
        search_depth="advanced", # 开启高级深度搜索
        include_raw_content=True # 尽可能提取网页正文
    )
    return search_tool

# ==========================================
# 🌟 Arxiv 顶级学术检索引擎
# ==========================================
@tool
def arxiv_search_tool(query: str) -> str:
    """从 Arxiv 检索最新的学术论文。当用户需要查阅前沿技术、学术研究报告或论文文献时，调用此工具。"""
    try:
        # top_k_results: 返回前3篇；doc_content_chars_max: 限制字符数防 OOM
        arxiv = ArxivAPIWrapper(top_k_results=3, doc_content_chars_max=3000)
        return arxiv.run(query)
    except Exception as e:
        return f"Arxiv 检索失败: {e}"

# ==========================================
# 🌟 结构化表格数据读取器
# ==========================================
@tool
def read_excel_csv_tool(filename: str) -> str:
    """读取本地知识库中的 Excel 或 CSV 表格文件。当用户询问表格里的数据、要求分析数据走势时调用。"""
    if not os.path.exists(UPLOAD_DIR):
        return "本地无任何文件。"
        
    files = os.listdir(UPLOAD_DIR)
    # 模糊匹配找到表格文件
    matched_file = next((f for f in files if filename.lower() in f.lower() and f.endswith(('.csv', '.xlsx', '.xls'))), None)
    
    if not matched_file:
        return f"未能找到包含 '{filename}' 的表格文件（请确保格式为 csv/xlsx）。"
        
    file_path = os.path.join(UPLOAD_DIR, matched_file)
    
    try:
        # 使用 Pandas 读取数据
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
            
        # 为了防止数据太大撑爆上下文，这里默认提取前 10 行并转为 Markdown 格式
        # 同时告诉大模型该表的数据规模
        summary = f"已成功读取表格 `{matched_file}`。\n"
        summary += f"该表共有 {df.shape[0]} 行, {df.shape[1]} 列。\n"
        summary += "以下是表格的前 10 行数据预览：\n"
        summary += df.head(10).to_markdown()
        
        return summary
    except Exception as e:
        return f"解析表格数据失败: {e}"

# ========== 下面是用于单独测试这个工具的代码 ==========
if __name__ == "__main__":
    print("正在测试 Tavily 联网搜索工具...")
    search_tool = get_web_search_tool(max_results=2)
    
    # 让它去搜一下今天的新闻
    query = "今天AI领域有什么大新闻？"
    print(f"搜索词: {query}\n")
    
    results = search_tool.invoke({"query": query})
    print("搜索结果: ", results)