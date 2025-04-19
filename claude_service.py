import os
import anthropic
from typing import Optional

class ClaudeService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key not provided and not found in environment variables")
        
        self.client = anthropic.Anthropic(api_key=self.api_key)
    
    def estimate_task_time(self, task_description: str) -> float:
        """
        Use Claude to estimate how many hours a task might take based on its description.
        
        Args:
            task_description: Description of the task
            
        Returns:
            Estimated hours to complete the task
        """
        prompt = f"""
        Based on the following task description, estimate how many hours it would take an average person to complete.
        Please respond with just a number representing hours (can be a decimal).
        
        Task: {task_description}
        
        Estimated hours:
        """
        
        message = self.client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=50,
            temperature=0.0,
            system="You are a helpful assistant that estimates how long tasks take to complete. Respond only with the number of hours.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        try:
            # Extract the number from Claude's response
            time_str = message.content[0].text.strip()
            return float(time_str)
        except (ValueError, IndexError):
            # Fallback if we can't parse Claude's response
            return 1.0 