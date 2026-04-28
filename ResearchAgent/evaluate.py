import asyncio
import json
import time
import datetime
import os
from pathlib import Path
from typing import List, Dict, Any
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field, AliasChoices
from core.llm import get_llm
from agents.chat_agent import normal_chat_agent

judge_llm = get_llm()

class EvaluationResult(BaseModel):
    score: float = Field(description="Score between 0.0 and 1.0")
    reason: str = Field(
        validation_alias=AliasChoices('reason', 'reasoning', 'explanation'), 
        description="Brief justification for the score"
    )

# Expanded dataset for robust evaluation
EVAL_DATASET = [
    {
        "id": "eval_01_chit_chat",
        "input": "Hello, I am a new developer.",
        "expected_tools": [], 
        "rubric": "Response must be friendly, brief, and welcoming."
    },
    {
        "id": "eval_02_local_retrieval",
        "input": "Based on the internal system uploaded files, what are the core conclusions?",
        # Local retrieval is now handled internally by Agentic RAG, not exposed as a top-level LangChain tool
        "expected_tools": [], 
        "rubric": "Response must attempt to answer based on local knowledge or gracefully state if no relevant files were found."
    },
    {
        "id": "eval_03_identity_check",
        "input": "Who am I?",
        "expected_tools": [],
        # Removing the strict "must state it does not have personal memory" rule because our system *does* have persistent memory now.
        "rubric": "Response must acknowledge the user's identity based on historical context or politely ask if unknown."
    },
    {
        "id": "eval_04_web_search",
        "input": "What is the latest news about solid-state batteries?",
        "expected_tools": ["tavily_search_results_json"],
        "rubric": "Response must contain factual information regarding recent events."
    }
]

async def evaluate_metric(query: str, response: str, metric_type: str, context: str = "") -> dict:
    grader = judge_llm.with_structured_output(EvaluationResult)
    
    if metric_type == "relevance":
        prompt = f"Assess the relevance of the response to the query. Score 1.0 if perfectly relevant, 0.0 if completely irrelevant. You must return the evaluation in JSON format.\nQuery: {query}\nResponse: {response}"
    elif metric_type == "faithfulness":
        prompt = f"Assess if the response contains hallucinations. Score 1.0 if completely faithful and factual, 0.0 if hallucinated or fabricated. You must return the evaluation in JSON format.\nQuery: {query}\nResponse: {response}"
    elif metric_type == "rubric":
        prompt = f"Assess if the response meets the rubric. Score 1.0 if it strictly meets it, 0.0 if not. You must return the evaluation in JSON format.\nQuery: {query}\nResponse: {response}\nRubric: {context}"
    else:
        return {"score": 0.0, "reason": "Unknown metric"}

    try:
        res = await grader.ainvoke([HumanMessage(content=prompt)])
        return {"score": res.score, "reason": res.reason}
    except Exception as e:
        return {"score": 0.0, "reason": f"Evaluation error: {str(e)}"}

async def run_evaluations():
    print("Starting Automated RAGAS-style Evaluation Pipeline...")
    
    results_summary = {
        "total_cases": len(EVAL_DATASET),
        "avg_relevance": 0.0,
        "avg_faithfulness": 0.0,
        "avg_rubric_score": 0.0,
        "details": []
    }
    
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    for idx, test in enumerate(EVAL_DATASET):
        print(f"\nProcessing case [{idx+1}/{len(EVAL_DATASET)}]: {test['id']}")
        
        state = {"messages": [HumanMessage(content=test['input'])], "current_route": "", "search_keywords": []}
        start_time = time.time()
        
        actual_trajectory = []
        final_response = ""
        
        try:
            async for event in normal_chat_agent.astream_events(state, version="v2"):
                kind = event["event"]
                if kind == "on_tool_start":
                    actual_trajectory.append(event.get("name"))
                elif kind == "on_chat_model_stream":
                    node_name = event.get("metadata", {}).get("langgraph_node", "")
                    chunk = event["data"]["chunk"].content
                    if isinstance(chunk, str) and node_name != "router": 
                        final_response += chunk
        except Exception as e:
            final_response = f"Execution error: {e}"
            
        latency = time.time() - start_time
        
        # Concurrent evaluation of multiple metrics
        eval_tasks = [
            evaluate_metric(test["input"], final_response, "relevance"),
            evaluate_metric(test["input"], final_response, "faithfulness"),
            evaluate_metric(test["input"], final_response, "rubric", test["rubric"])
        ]
        relevance_res, faith_res, rubric_res = await asyncio.gather(*eval_tasks)
        
        # Check trajectory
        traj_passed = all(tool in actual_trajectory for tool in test["expected_tools"])
        
        case_result = {
            "id": test["id"],
            "input": test["input"],
            "latency": round(latency, 2),
            "trajectory_passed": traj_passed,
            "actual_tools": actual_trajectory,
            "metrics": {
                "relevance": relevance_res,
                "faithfulness": faith_res,
                "rubric_compliance": rubric_res
            }
        }
        results_summary["details"].append(case_result)
        
        print(f"  Latency: {latency:.2f}s")
        print(f"  Relevance Score: {relevance_res['score']}")
        print(f"  Faithfulness Score: {faith_res['score']}")
        print(f"  Rubric Score: {rubric_res['score']}")

    # Calculate averages
    if results_summary["total_cases"] > 0:
        results_summary["avg_relevance"] = sum(r["metrics"]["relevance"]["score"] for r in results_summary["details"]) / results_summary["total_cases"]
        results_summary["avg_faithfulness"] = sum(r["metrics"]["faithfulness"]["score"] for r in results_summary["details"]) / results_summary["total_cases"]
        results_summary["avg_rubric_score"] = sum(r["metrics"]["rubric_compliance"]["score"] for r in results_summary["details"]) / results_summary["total_cases"]

    print("\n" + "="*50)
    print("Evaluation Summary:")
    print(f"Average Relevance: {results_summary['avg_relevance']:.2f}")
    print(f"Average Faithfulness: {results_summary['avg_faithfulness']:.2f}")
    print(f"Average Rubric Score: {results_summary['avg_rubric_score']:.2f}")
    
    # Save results
    output_dir = Path("evaluation_result")
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"eval_report_{int(time.time())}.json"
    
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results_summary, f, ensure_ascii=False, indent=2)
        
    print(f"\nQuantified evaluation report saved locally: {report_path.resolve()}")

if __name__ == "__main__":
    asyncio.run(run_evaluations())