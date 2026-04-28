import asyncio
import json
import time
import datetime
import os
from pathlib import Path
from typing import List, Dict, Any
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from core.llm import get_llm
from agents.chat_agent import normal_chat_agent

judge_llm = get_llm()

class EvaluationResult(BaseModel):
    score: float = Field(description="Score between 0.0 and 1.0")
    reason: str = Field(description="Brief justification for the score")

# Expanded dataset for robust evaluation
EVAL_DATASET = [
    {
        "id": "eval_01_chit_chat",
        "input": "Hello, I am a new developer.",
        "expected_tools": [], 
        "rubric": "Response must be friendly, brief, and welcoming. Do not invent unprovided information."
    },
    {
        "id": "eval_02_local_file_listing",
        "input": "Which files have been uploaded to the system?",
        "expected_tools": ["list_local_files"],
        "rubric": "Response must accurately list the filenames returned by the tool."
    },
    {
        "id": "eval_03_document_summary",
        "input": "Summarize the core conclusions of the .txt files in the knowledge base.",
        "expected_tools": ["read_full_document"],
        "rubric": "Response must be an objective summary based on file content."
    },
    {
        "id": "eval_04_identity_check",
        "input": "Who am I?",
        "expected_tools": [],
        "rubric": "Response must state that the AI does not have personal memory of the user unless provided."
    },
    {
        "id": "eval_05_web_search",
        "input": "What is the latest news about solid-state batteries?",
        "expected_tools": ["tavily_search_results_json"],
        "rubric": "Response must contain recent factual information."
    }
]

async def evaluate_metric(query: str, response: str, metric_type: str, context: str = "") -> dict:
    grader = judge_llm.with_structured_output(EvaluationResult)
    
    if metric_type == "relevance":
        prompt = f"Assess the relevance of the response to the query. Score 1.0 if perfectly relevant, 0.0 if completely irrelevant.\nQuery: {query}\nResponse: {response}"
    elif metric_type == "faithfulness":
        prompt = f"Assess if the response contains hallucinations. Score 1.0 if completely faithful and factual, 0.0 if hallucinated or fabricated.\nQuery: {query}\nResponse: {response}"
    elif metric_type == "rubric":
        prompt = f"Assess if the response meets the rubric. Score 1.0 if it strictly meets it, 0.0 if not.\nQuery: {query}\nResponse: {response}\nRubric: {context}"
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
                    chunk = event["data"]["chunk"].content
                    if isinstance(chunk, str): 
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