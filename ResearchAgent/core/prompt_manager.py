import os
import json

class PromptManager:
    def __init__(self):
        # 定位到 prompts/agents_prompt.json
        self.config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            "prompts", 
            "agents_prompt.json"
        )
        self.prompts = self._load_prompts()

    def _load_prompts(self):
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 提示词文件加载失败: {e}")
            return {}

    def get(self, agent_name: str, prompt_key: str) -> str:
        """获取指定的提示词模板"""
        return self.prompts.get(agent_name, {}).get(prompt_key, "")

# 全局单例
prompt_manager = PromptManager()