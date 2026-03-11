from openai import OpenAI
from qwen_agent.agents import Assistant

class PlannerModel():
    def __init__(self, model_name, api_key, base_url):
        self.model_name = model_name
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def forward(self, messages):
        try:
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                # extra_body={"enable_thinking": True},
                temperature=0.0,
                top_p=1.0,
                max_tokens=8192,
                # stream=True,
            )
            return 0, completion.choices[0].message.content
            # return 0, completion
        except Exception as e:   
            return 1, f"OpenAI Request ERROR: {e}"
        
class SupervisorModel():
    def __init__(self, model_name, api_key, base_url):
        self.model_name = model_name
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def forward(self, messages):
        try:
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                # extra_body={"enable_thinking": True},
                # temperature=0.0,
                # top_p=1.0,
                max_tokens=8192,
                # stream=True,
            )
            return True, completion.choices[0].message.content
            # return 0, completion
        except Exception as e:   
            return False, f"OpenAI Request ERROR: {e}"
        
class RobotModel():
    def __init__(self, model_name, api_key, base_url, tools, system_prompt):
        self.model_name = model_name
        llm_cfg = {
            # Use a model service compatible with the OpenAI API, such as vLLM or Ollama:
            'model': model_name,
            'model_server': base_url,  # base_url, also known as api_base
            'api_key': api_key,
            # (Optional) LLM hyperparameters for generation:
            'generate_cfg': {
                # 'max_tokens': 4096,
                "extra_body": {"enable_thinking": True},
            }
        }
        self.bot = Assistant(llm=llm_cfg,
                system_message=system_prompt,
                function_list=tools
                )

    def forward(self, user_prompt):
        messages = [
            {'role': 'user', 'content': user_prompt}
        ]
        last_response = None
        for response in self.bot.run(messages=messages):
            last_response = response
        return last_response