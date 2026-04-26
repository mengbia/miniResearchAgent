from langchain_tavily import TavilySearch
from core.config import TAVILY_API_KEY
from langchain_core.tools import tool

import os

os.environ["TAVILY_API_KEY"] = TAVILY_API_KEY

def get_web_search_tool(max_results: int = 4):
    """
    Enhanced web search tool.
    Uses Tavily's advanced search to retrieve high-quality content.
    """
    if not TAVILY_API_KEY:
        raise ValueError("TAVILY_API_KEY not configured. Please set it in the .env file.")
        
    os.environ["TAVILY_API_KEY"] = TAVILY_API_KEY
    
    # Configure search tool with advanced depth and raw content extraction
    search_tool = TavilySearch(
        max_results=max_results,
        search_depth="advanced", 
        include_raw_content=True 
    )
    return search_tool

@tool
def arxiv_search_tool(query: str) -> str:
    """Retrieve academic papers from Arxiv for technical or scientific research."""
    try:
        # Return top 3 results; limit characters to prevent memory issues.
        arxiv = ArxivAPIWrapper(top_k_results=3, doc_content_chars_max=3000)
        return arxiv.run(query)
    except Exception as e:
        return f"Arxiv retrieval failed: {e}"

@tool
def read_excel_csv_tool(filename: str) -> str:
    """Read local Excel or CSV files from the knowledge base for data analysis."""
    if not os.path.exists(UPLOAD_DIR):
        return "No local files found."
        
    files = os.listdir(UPLOAD_DIR)
    matched_file = next((f for f in files if filename.lower() in f.lower() and f.endswith(('.csv', '.xlsx', '.xls'))), None)
    
    if not matched_file:
        return f"Could not find a table file matching '{filename}' (CSV or XLSX expected)."
        
    file_path = os.path.join(UPLOAD_DIR, matched_file)
    
    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
            
        summary = f"Successfully read table `{matched_file}`.\n"
        summary += f"Dataset dimensions: {df.shape[0]} rows, {df.shape[1]} columns.\n"
        summary += "Preview of the first 10 rows:\n"
        summary += df.head(10).to_markdown()
        
        return summary
    except Exception as e:
        return f"Failed to parse table data: {e}"

if __name__ == "__main__":
    print("Testing Tavily web search tool...")
    search_tool = get_web_search_tool(max_results=2)
    
    query = "Latest news in the field of AI."
    print(f"Query: {query}\n")
    
    results = search_tool.invoke({"query": query})
    print("Search results: ", results)
