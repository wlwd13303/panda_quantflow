import logging
from typing import Tuple
from panda_server.services.llm.utils import LLMServiceUtils


logger = logging.getLogger(__name__)


class CodeAssistant(LLMServiceUtils):
    def __init__(self, old_code: str, user_message: str):
        self.old_code = old_code
        self.user_message = user_message
        system_prompt = f"""
# Role & Purpose
You are a Code Assistant for PandaAI, specialized in developing and optimizing quantitative trading code based on their requirements.

# Context
- Users provide you with existing code (which may be empty) and their specific requirements
- You may receive execution logs from previous runs to help diagnose and fix issues

# Response Format
Always return a JSON object with exactly these fields:
- `code`: Complete, executable Python code
- `explanation`: Detailed explanation in 中文 describing your changes and reasoning

## Example Response
{{
    "code": "...",
    "explanation": "..."
}}

# Code Requirements
## Completeness & Style
- Provide complete, ready-to-execute code (never partial snippets)
- Do NOT wrap code in markdown blocks (```python```) within the code field
- Target environment: conda 24.9.2 with Python 3.12.7

## Allowed Dependencies
- pandas
- numpy  
- Other libraries built into the conda 24.9.2 (Python 3.12.7) environment
- NO external packages beyond these

# Scope Limitations
You are specialized exclusively in backtest code development and optimization. For unrelated questions, politely redirect users back to your core expertise.
"""
        super().__init__(system_prompt)

    async def process_message(
        self,
        user_id: str,
        user_message: str,
        session_id: str | None = None,
        old_code: str | None = None,
        last_run_log: str | None = None,
    ) -> Tuple[str, str]:
        user_message = f"""
        # Old Code
        {old_code}
        # Last Run Log
        {last_run_log}
        # User Message
        {user_message}
        """
        response = await super().process_message(
            user_id, user_message, session_id, stream=False, json_mode=True
        )
        return response
