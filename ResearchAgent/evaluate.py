import asyncio
import json
import time
import datetime
import os
from pathlib import Path
from typing import List, Dict, Any
from langchain_core.messages import HumanMessage, SystemMessage
from core.llm import get_llm
from agents.chat_agent import normal_chat_agent

judge_llm = get_llm()

# Gold Standard Dataset for evaluation
ANTHROPIC_EVAL_DATASET = [
    {
        "id": "eval_01_chit_chat",
        "input": "Hello, I am a new developer.",
        "expected_trajectory": [], 
        "rubric": "Response must be friendly, brief, and welcoming. Do not invent unprovided information."
    },
    {
        "id": "eval_02_tool_selection",
        "input": "Which files have been uploaded to the system?",
        "expected_trajectory": ["list_local_files"],
        "rubric": "Response must accurately list the filenames returned by the tool without omissions or hallucinations."
    },
    {
        "id": "eval_03_deep_read",
        "input": "Summarize the core conclusions of the .txt files in the knowledge base.",
        "expected_trajectory": ["read_full_document"],
        "rubric": "Response must be an objective summary based on file content, clearly structured, and free of hallucinations."
    }
]

async def rubric_based_judge(query: str, response: str, rubric: str) -> dict:
    """Evaluates agent responses using an LLM based on a provided rubric."""
    judge_prompt = f"""You are an expert grading assistant.
Evaluate the AI's response based strictly on the provided rubric.

[User Input]: {query}
[AI Response]: {response}
[Grading Rubric]: {rubric}

Provide your evaluation as a JSON object with two keys:
- "pass": boolean (true if it meets the rubric, false otherwise)
- "reason": string (brief justification)
"""
    try:
        result = await judge_llm.ainvoke([SystemMessage(content=judge_prompt)])
        
        content = result.content.strip()
        if content.startswith("```json"): 
            content = content[7:-3]
            
        return json.loads(content)
    except Exception as e:
        print(f"  [Judge Parsing Failed]: {e}")
        return {"pass": False, "reason": "Judge parsing failed"}

async def run_anthropic_evals():
    print("Starting Anthropic evaluation engine...\n" + "="*50)
    
    results = {"total": len(ANTHROPIC_EVAL_DATASET), "trajectory_pass": 0, "output_pass": 0}
    
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_lines = [
        f"# Agent Evaluation Report",
        f"**Generated at**: {current_time}",
        f"**Total Test Cases**: {results['total']}",
        "\n---",
        "## Detailed Test Results\n"
    ]

    for idx, test in enumerate(ANTHROPIC_EVAL_DATASET):
        print(f"\n[{idx+1}/{results['total']}] Running evaluation: {test['id']}")
        
        state = {"messages": [HumanMessage(content=test['input'])]}
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
            print(f"  Execution error: {e}")
            final_response = f"Execution error: {e}"
            
        latency = time.time() - start_time
        
        traj_passed = (actual_trajectory == test["expected_trajectory"])
        if traj_passed: 
            results["trajectory_pass"] += 1
            
        eval_result = await rubric_based_judge(test["input"], final_response, test["rubric"])
        if eval_result.get("pass"): 
            results["output_pass"] += 1
            
        print(f"  Latency: {latency:.2f}s")
        print(f"  Trajectory Validation: {'PASS' if traj_passed else 'FAIL'} (Expected: {test['expected_trajectory']}, Actual: {actual_trajectory})")
        print(f"  Output Validation: {'PASS' if eval_result.get('pass') else 'FAIL'}")
        print(f"  Reasoning: {eval_result.get('reason')}")

        report_lines.extend([
            f"### Test Case [{idx+1}/{results['total']}]: `{test['id']}`",
            f"- **Input**: {test['input']}",
            f"- **Expected Trajectory**: `{test['expected_trajectory']}`",
            f"- **Actual Trajectory**: `{actual_trajectory}`",
            f"- **Trajectory Validation**: {'PASS' if traj_passed else 'FAIL'}",
            f"- **Output Validation**: {'PASS' if eval_result.get('pass') else 'FAIL'}",
            f"- **Reasoning**: {eval_result.get('reason')}",
            f"- **Latency**: {latency:.2f}s",
            "\n"
        ])

    print("\n" + "="*50)
    print(f"Evaluation Summary: Trajectory Accuracy {results['trajectory_pass']}/{results['total']} | Output Compliance {results['output_pass']}/{results['total']}")
    
    report_lines.extend([
        "---",
        "## Evaluation Summary",
        f"- **Trajectory Accuracy**: {results['trajectory_pass']} / {results['total']}",
        f"- **Output Compliance**: {results['output_pass']} / {results['total']}",
        ""
    ])

    if results['trajectory_pass'] == results['total'] and results['output_pass'] == results['total']:
        conclusion = "Conclusion: All tests passed. The Agent meets the deployment standards."
        print(conclusion)
    else:
        conclusion = "Conclusion: Optimization required. Please review the failed cases and adjust system prompts or tool descriptions."
        print(conclusion)
    
    report_lines.append(conclusion)

    output_dir = Path("evaluation_result")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    base_filename = "evaluation_report"
    extension = ".md"
    
    report_path = output_dir / f"{base_filename}{extension}"
    
    counter = 1
    while report_path.exists():
        report_path = output_dir / f"{base_filename}_{counter}{extension}"
        counter += 1

    try:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))
        print(f"\nFinal evaluation report saved locally: {report_path.resolve()}")
    except Exception as e:
        print(f"\nFailed to save report locally: {e}")

if __name__ == "__main__":
    asyncio.run(run_anthropic_evals())
