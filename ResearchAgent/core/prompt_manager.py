import os
import json

class PromptManager:
    def __init__(self):
        # Path to prompts/agents_prompt.json
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
            print(f"Failed to load prompts: {e}")
            return {}

    def get(self, agent_name: str, prompt_key: str) -> str:
        """Retrieves the specified prompt template."""
        return self.prompts.get(agent_name, {}).get(prompt_key, "")

prompt_manager = PromptManager()
