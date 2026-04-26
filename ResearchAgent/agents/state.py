from typing import TypedDict, List, Dict, Any, Annotated, Union
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
import operator

"""
In LangGraph, when multiple nodes (e.g., web and local specialists) run in parallel, 
they may attempt to overwrite the same 'sources' list. To merge their results correctly, 
we use a custom reducer to handle concurrent updates.
"""

def reduce_sources(left: List[Dict[str, str]], right: Union[List[Dict[str, str]], Dict[str, Any]]) -> List[Dict[str, str]]:
    """State reducer to handle concurrent updates and data consolidation."""
    if left is None: left = []
    
    # Mode A: Overwrite
    # Used by filter nodes to clear existing data and replace it with a cleaned set.
    if isinstance(right, dict) and right.get("action") == "overwrite":
        return right.get("data", [])
        
    # Mode B: Concurrent Merge
    # Used by worker nodes to append new findings.
    if not isinstance(right, list): right = []
    
    merged = {}
    for s in left:
        merged[s.get("url", "")] = s
    for s in right:
        merged[s.get("url", "")] = s
        
    return list(merged.values())

class AgentState(TypedDict):
    user_query: str
    messages: Annotated[List[Any], operator.add]
    plan: List[Dict[str, str]]
    sources: Annotated[List[Dict[str, str]], reduce_sources]
    report: str
    loop_count: int
