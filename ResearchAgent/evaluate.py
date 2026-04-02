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

# 初始化裁判大脑
judge_llm = get_llm()

# ==========================================
# 1. 黄金测试集 (Gold Standard Dataset)
# ==========================================
ANTHROPIC_EVAL_DATASET = [
    {
        "id": "eval_01_chit_chat",
        "input": "你好，我是新来的开发。",
        "expected_trajectory": [], 
        "rubric": "回答必须友好、简短，且包含欢迎的意思。不能编造未提供的信息。"
    },
    {
        "id": "eval_02_tool_selection",
        "input": "系统里现在传了哪些文件？",
        "expected_trajectory": ["list_local_files"],
        "rubric": "回答必须准确列出工具返回的文件名列表，不能遗漏，也不能加上不存在的文件。"
    },
    {
        "id": "eval_03_deep_read",
        "input": "请总结知识库里 .txt 文件的核心结论。",
        "expected_trajectory": ["read_full_document"],
        "rubric": "回答必须是基于文件内容的客观总结，结构清晰，严禁包含幻觉（编造文件中没有的结论）。"
    }
]

# ==========================================
# 2. 终态裁判引擎 (Output Evaluator)
# ==========================================
async def rubric_based_judge(query: str, response: str, rubric: str) -> dict:
    """让大模型根据指定的量规（Rubric）充当裁判"""
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
        print(f"  [裁判解析失败]: {e}")
        return {"pass": False, "reason": "Judge parsing failed"}

# ==========================================
# 3. 轨迹与端到端执行引擎 (Trajectory & E2E Runner)
# ==========================================
async def run_anthropic_evals():
    print("🚀 启动 Anthropic 标准评估引擎...\n" + "="*50)
    
    results = {"total": len(ANTHROPIC_EVAL_DATASET), "trajectory_pass": 0, "output_pass": 0}
    
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_lines = [
        f"# Agent 评估报告",
        f"**生成时间**: {current_time}",
        f"**总测试用例数**: {results['total']}",
        "\n---",
        "## 详细测试结果\n"
    ]

    for idx, test in enumerate(ANTHROPIC_EVAL_DATASET):
        print(f"\n[{idx+1}/{results['total']}] 运行评估: {test['id']}")
        
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
            print(f"  ❌ 执行异常: {e}")
            final_response = f"执行异常: {e}"
            
        latency = time.time() - start_time
        
        traj_passed = (actual_trajectory == test["expected_trajectory"])
        if traj_passed: 
            results["trajectory_pass"] += 1
            
        eval_result = await rubric_based_judge(test["input"], final_response, test["rubric"])
        if eval_result.get("pass"): 
            results["output_pass"] += 1
            
        print(f"  ⏱️ 耗时: {latency:.2f}s")
        print(f"  🛤️ 轨迹校验: {'✅ PASS' if traj_passed else '❌ FAIL'} (预期: {test['expected_trajectory']}, 实际: {actual_trajectory})")
        print(f"  🎯 输出校验: {'✅ PASS' if eval_result.get('pass') else '❌ FAIL'}")
        print(f"  📝 裁判理由: {eval_result.get('reason')}")

        report_lines.extend([
            f"### 测试用例 [{idx+1}/{results['total']}]: `{test['id']}`",
            f"- **输入**: {test['input']}",
            f"- **预期轨迹**: `{test['expected_trajectory']}`",
            f"- **实际轨迹**: `{actual_trajectory}`",
            f"- **轨迹校验**: {'✅ PASS' if traj_passed else '❌ FAIL'}",
            f"- **输出校验**: {'✅ PASS' if eval_result.get('pass') else '❌ FAIL'}",
            f"- **裁判理由**: {eval_result.get('reason')}",
            f"- **耗时**: {latency:.2f}s",
            "\n"
        ])

    # ==========================================
    # 4. 评估总结报告与本地存储
    # ==========================================
    print("\n" + "="*50)
    print(f"📊 评估总结: 轨迹准确率 {results['trajectory_pass']}/{results['total']} | 输出达标率 {results['output_pass']}/{results['total']}")
    
    report_lines.extend([
        "---",
        "## 📊 评估总结",
        f"- **轨迹准确率**: {results['trajectory_pass']} / {results['total']}",
        f"- **输出达标率**: {results['output_pass']} / {results['total']}",
        ""
    ])

    if results['trajectory_pass'] == results['total'] and results['output_pass'] == results['total']:
        conclusion = "💡 **结论**: 完美通过！你的 Agent 表现极佳，达到了发布标准！"
        print("💡 结论: 完美通过！你的 Agent 表现极佳，达到了发布标准！")
    else:
        conclusion = "💡 **结论**: 还有优化空间，请根据失败用例的裁判理由，调整对应的系统提示词或工具描述。"
        print("💡 结论: 还有优化空间，请根据失败用例的裁判理由，调整对应的系统提示词或工具描述。")
    
    report_lines.append(conclusion)

    # ==========================================
    # 5. 自动创建文件夹并处理文件名自增
    # ==========================================
    output_dir = Path("evaluation_result")
    # 如果文件夹不存在，自动创建
    output_dir.mkdir(parents=True, exist_ok=True)
    
    base_filename = "evaluation_report"
    extension = ".md"
    
    # 拼接初始路径
    report_path = output_dir / f"{base_filename}{extension}"
    
    # 检查文件是否存在，如果存在则递增序号
    counter = 1
    while report_path.exists():
        report_path = output_dir / f"{base_filename}_{counter}{extension}"
        counter += 1

    try:
        # 写入文件
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))
        print(f"\n💾 最终评估报告已成功保存至本地: {report_path.resolve()}")
    except Exception as e:
        print(f"\n❌ 保存报告到本地失败: {e}")

if __name__ == "__main__":
    asyncio.run(run_anthropic_evals())