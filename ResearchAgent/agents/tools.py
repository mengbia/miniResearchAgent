from langchain_community.tools.tavily_search import TavilySearchResults
from core.config import TAVILY_API_KEY
import os

# 确保环境变量里有 TAVILY_API_KEY，LangChain 底层会自动去这里找
os.environ["TAVILY_API_KEY"] = TAVILY_API_KEY

def get_web_search_tool(max_results: int = 3):
    """
    获取联网搜索工具
    :param max_results: 每次搜索返回的网页数量，深度研究可以设大一点
    """
    # 实例化 Tavily 搜索工具
    # search_depth="advanced" 表示深度搜索，返回更详细的网页正文片段
    tool = TavilySearchResults(
        max_results=max_results,
        search_depth="advanced",
        include_answer=True,
        include_raw_content=True
    )
    return tool

# ========== 下面是用于单独测试这个工具的代码 ==========
if __name__ == "__main__":
    print("正在测试 Tavily 联网搜索工具...")
    search_tool = get_web_search_tool(max_results=2)
    
    # 让它去搜一下今天的新闻
    query = "今天AI领域有什么大新闻？"
    print(f"搜索词: {query}\n")
    
    results = search_tool.invoke({"query": query})
    print("搜索结果: ", results)