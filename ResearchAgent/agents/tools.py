from langchain_community.tools.tavily_search import TavilySearchResults
from core.config import TAVILY_API_KEY
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

# ========== 下面是用于单独测试这个工具的代码 ==========
if __name__ == "__main__":
    print("正在测试 Tavily 联网搜索工具...")
    search_tool = get_web_search_tool(max_results=2)
    
    # 让它去搜一下今天的新闻
    query = "今天AI领域有什么大新闻？"
    print(f"搜索词: {query}\n")
    
    results = search_tool.invoke({"query": query})
    print("搜索结果: ", results)