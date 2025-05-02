import os
import anthropic
from typing import Optional

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class ClaudeService:
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key not provided and not found in environment variables")
        
        self.client = anthropic.Anthropic(api_key=self.api_key)
    
    ## Estimate task time
    def estimate_task_time(self, task_description: str) -> tuple[str, str]:
        """
        Estimate how many hours a task might take.
        Returns (prompt, response_text)
        """
        
        prompt = f"""
                    You are a time estimation assistant. Your job is to estimate how long a task takes for an average person.

                    Respond **only with a number**, in decimal hours (e.g., 1.5 means 1 hour and 30 minutes).
                    Do not include any explanation or context. Do not write units or words like 'hours'.

                    Task: {task_description}

                    Estimated hours:
                """
        
        try:
            msg = self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=50,
                temperature=0.0,
                system="You are a helpful assistant that estimates how long tasks take to complete. Respond only with the number of hours.",
                messages=[{"role": "user", "content": prompt}],
            )
            response_text = msg.content[0].text.strip()
            logger.debug(f"Claude raw response: {response_text}")
            return prompt, response_text

        except Exception as e:
            logger.warning(f"Failed to estimate task time: {e}")
            return prompt, "1.0"

    ## Generate summary for the day 
    def summarize_the_day(self, tasks: list) -> str:
        
        """
        Ask Claude to summarize the workload for the day and provide insights.
        
        Args:
            tasks: List of Task objects scheduled for today
        
        Returns:
            A human-readable insight summary
        """

        if not tasks:
            return "No tasks today. You can relax or plan ahead."

        task_list = "\n".join([f"- {t.description} ({t.estimated_hours:.1f} hrs)" for t in tasks])
        
        prompt = f"""
                    You are a thoughtful productivity assistant helping users summzarize their workload for the day.

                    Here is a list of tasks scheduled for today:
                    {task_list}

                    Based on this, provide a short summary (1-2 sentences) with suggestions if needed. Focus on feasibility, potential overload, or chunking large tasks.
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
            logger.warning(f"Failed to summarize on tasks: {e}")
            return "Could not generate a summary for today."
