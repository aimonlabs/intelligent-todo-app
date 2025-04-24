import os
import anthropic
from typing import Optional

from aimon import Detect
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

## AIMon decorator for instruction adherence
detect = Detect(
    values_returned=["context", "generated_text", "instructions"],
    config={"instruction_adherence": {"detector_name": "default"}},
    api_key=os.getenv("AIMON_API_KEY"),
    application_name="todo_agent",
    model_name="claude_api_model",
    publish=True
)

class ClaudeService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key not provided and not found in environment variables")
        
        self.client = anthropic.Anthropic(api_key=self.api_key)
    
    ## Estimate task time

    @detect
    def estimate_task_time(self, task_description: str) -> float:
        
        """
        Use Claude to estimate how many hours a task might take based on its description.
        
        Args:
            task_description: Description of the task
            
        Returns:
            Estimated hours to complete the task
        """

        prompt = f"""
        You are a time estimation assistant. Your job is to estimate how long a task takes for an average person.

        Respond **only with a number**, in decimal hours (e.g., 1.5 means 1 hour and 30 minutes). 
        Do not include any explanation or context. Do not write units or words like 'hours'.

        Task: {task_description}
        
        Estimated hours:
        """

        instructions = (
            "1. Respond only with a numeric value (e.g., 1.5).\n"
            "2. Do not include the word 'hours' or any units.\n"
            "3. Do not include any explanation, description, or justification.\n"
        )

        try:

            message = self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=50,
                temperature=0.0,
                system="You are a helpful assistant that estimates how long tasks take to complete. Respond only with the number of hours.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
        
            response_text = message.content[0].text.strip()
            logger.debug(f"Claude raw response: {response_text}")
            return prompt, response_text, instructions
        
        except Exception as e:
            logger.warning(f"Failed to estimate task time: {e}")
            ## Fallback response
            return prompt, "1.0", instructions


    ## Reflect on the day (generate summary)
    def reflect_on_day(self, tasks: list) -> str:
        
        """
        Ask Claude to reflect on the workload for the day and provide insights.
        
        Args:
            tasks: List of Task objects scheduled for today
        
        Returns:
            A human-readable insight summary
        """

        if not tasks:
            return "No tasks today. You can relax or plan ahead."

        task_list = "\n".join([f"- {t.description} ({t.estimated_hours:.1f} hrs)" for t in tasks])
        
        prompt = f"""
                    You are a thoughtful productivity assistant helping users reflect on their workload.

                    Here is a list of tasks scheduled for today:
                    {task_list}

                    Based on this, provide a short reflective summary (1-2 sentences) with suggestions if needed. Focus on feasibility, potential overload, or chunking large tasks.
                """

        try:
            message = self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=100,
                temperature=0.4,
                system="You help people make sense of their daily task load and give human-like suggestions.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return message.content[0].text.strip()

        except Exception as e:
            logger.warning(f"Failed to reflect on tasks: {e}")
            return "Could not generate a reflection for today."
        