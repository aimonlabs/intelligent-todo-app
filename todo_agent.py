import os
import io
import json
import pytz
import logging
import contextlib
from datetime import datetime
from autogen import ConversableAgent
from typing import Dict, List, Optional
from task_model import Task, TaskStatus
from claude_service import ClaudeService
from reflection_agent import reflection_agent

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Pacific timezone for consistent datetime handling
pacific_tz = pytz.timezone('America/Los_Angeles')

class TodoAgent:
    def __init__(self, storage_path: str = "tasks.json", claude_api_key: Optional[str] = None):
        self.storage_path = storage_path
        self.tasks: Dict[str, Task] = self._load_tasks()
        self.claude_service = ClaudeService(api_key=claude_api_key)

        # Set up AG2 agent
        self.agent = ConversableAgent(
            name="Todo Agent",
            system_message="An agent that manages your todo list and helps you stay organized.",
        )
        
        # Register agent skills
        def create_task_skill(description: str, due_date_str: str, estimated_hours: Optional[float] = None):
            return self.create_task(description, due_date_str, estimated_hours)
            
        def list_tasks_skill(status: Optional[str] = None):
            return self.list_tasks(status)
            
        def update_task_skill(task_id: str, description: Optional[str] = None, 
                            due_date_str: Optional[str] = None, estimated_hours: Optional[float] = None,
                            status: Optional[str] = None):
            return self.update_task(task_id, description, due_date_str, estimated_hours, status)
            
        def delete_task_skill(task_id: str):
            return self.delete_task(task_id)
            
        def estimate_task_time_skill(description: str):
            return self.estimate_task_time(description)
            
        def mark_task_complete_skill(task_id: str):
            return self.mark_task_complete(task_id)
        
        # Register the functions with the agent
        self.agent.register_for_execution(
            {
                "create_task": create_task_skill,
                "list_tasks": list_tasks_skill,
                "update_task": update_task_skill,
                "delete_task": delete_task_skill,
                "estimate_task_time": estimate_task_time_skill,
                "mark_task_complete": mark_task_complete_skill
            }
        )
    
    def _load_tasks(self) -> Dict[str, Task]:
        """Load tasks from the storage file"""
        if not os.path.exists(self.storage_path):
            return {}
            
        try:
            with open(self.storage_path, "r") as f:
                tasks_data = json.load(f)
                
            tasks = {}
            for task_dict in tasks_data:
                # Create task from dictionary
                task = Task.from_dict(task_dict)
                tasks[task.task_id] = task
                
            return tasks
        except Exception as e:
            print(f"Error loading tasks: {e}")
            return {}
    
    def _save_tasks(self):
        """Save tasks to the storage file"""
        try:
            # Convert Task objects to dictionaries
            tasks_data = []
            for task in self.tasks.values():
                task_dict = task.to_dict()
                tasks_data.append(task_dict)
            
            with open(self.storage_path, "w") as f:
                json.dump(tasks_data, f, indent=2)
                
        except Exception as e:
            print(f"Error saving tasks: {e}")
    
    def create_task(self, description: str, due_date_str: str, estimated_hours: Optional[float] = None) -> Task:
        """Create a new task with optional time estimation"""
        # Parse the due date string
        due_date = datetime.fromisoformat(due_date_str)
        
        # If estimated_hours not provided, use Claude to estimate
        if estimated_hours is None:
            estimated_hours = self.estimate_task_time(description)
        
        # Create the task
        task = Task(
            title=description,  # Use description as title
            description=description,
            due_date=due_date,
            estimated_hours=estimated_hours
        )
        
        # Save the task
        self.tasks[task.task_id] = task
        self._save_tasks()
        
        return task
    
    def list_tasks(self, status: Optional[str] = None) -> List[Task]:
        """List all tasks, optionally filtered by status"""
        tasks = list(self.tasks.values())
        now = datetime.now(pacific_tz)

        if status:
            if status == "completed":
                tasks = [task for task in tasks if task.completed]
            elif status == "in_progress":
                tasks = [task for task in tasks if not task.completed and task.due_date >= now]
            elif status == "past_due":
                tasks = [task for task in tasks if not task.completed and task.due_date < now]

        # Ensure all datetimes are timezone-aware before sorting
        def get_due_date_for_sorting(task):
            if task.due_date and task.due_date.tzinfo is None:
                return pacific_tz.localize(task.due_date)
            return task.due_date

        tasks.sort(key=get_due_date_for_sorting)
        return tasks

    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID"""
        return self.tasks.get(task_id)
    
    def update_task(self, 
                   task_id: str, 
                   description: Optional[str] = None,
                   due_date_str: Optional[str] = None,
                   estimated_hours: Optional[float] = None,
                   status: Optional[str] = None) -> Optional[Task]:
        """Update a task's details"""
        task = self.tasks.get(task_id)
        if not task:
            return None
        
        # Update the fields if provided
        if description:
            task.title = description  # Update title too
            task.description = description
            
        if due_date_str:
            task.due_date = datetime.fromisoformat(due_date_str)
            
        if estimated_hours is not None:
            task.estimated_hours = estimated_hours
            
        if status:
            task.completed = status == TaskStatus.COMPLETED.value
        
        # Save the changes
        self._save_tasks()
        
        return task
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a task by ID"""
        if task_id in self.tasks:
            del self.tasks[task_id]
            self._save_tasks()
            return True
        return False
    

    def estimate_task_time(self, description: str) -> float:
        
        """
        Ask Claude for a numeric estimate, then validate it with ReflectionAgent.
        Retry 1 time if AIMon flags deviations from instructions.
        """

        max_retries = 1

        instructions = [
            "Respond only with a numeric value (e.g., 1.5).",
            "Do not include the word 'hours' or any units.",
            "Do not include any explanation, description, or justification.",
            "Keep the numeric value in the range 0 to 4.0"
        ]

        prompt = description

        for attempt in range(max_retries + 1):
            
            print()
            logger.debug(f"[Attempt {attempt + 1}] Estimating time for task: {description!r}")
            context, response_text = self.claude_service.estimate_task_time(prompt)
            logger.debug(f"Claude response: {response_text!r}")

            payload = json.dumps({
                "context": context,
                "generated_text": response_text,
                "instructions": instructions
            })

            ## Mute AG2’s internal tool output just for this call
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    tool_response = reflection_agent.execute_function({
                        "name": "check_instruction_adherence",
                        "arguments": payload
                    })

                result = json.loads(tool_response[1]["content"]) if tool_response[0] else {"issues": [{"error": "tool_failed"}]}
                issues = result.get("issues", [])

                if issues:
                    print()
                    logger.warning(f"AIMon flagged {len(issues)} issue(s) for task: {description!r}")
                    for issue in issues:
                        logger.warning(f"→ Instruction: {issue.get('instruction')}")
                        logger.warning(f"  Reason: {issue.get('explanation')}")
                else:
                    logger.info(f"No instruction violations for task: {description!r}")

            except Exception as e:
                logger.error(f"Reflection check failed: {e}")
                issues = [{"error": "parse_failed"}]

            if not issues:
                try:
                    return float(response_text.strip())
                except ValueError as ve:
                    logger.error(f"Could not parse response to float: {response_text!r} — {ve}")
                    break

            ## Retry with stricter prompt
            prompt = (
                f"{description}\n\n"
                "PLEASE ONLY OUTPUT a numeric estimate value of less than 3. "
                "No text, units, or commentary."
            )

        logger.warning(f"Max retries reached. Defaulting to 1.0 for task: {description!r}")
        return 1.0
    
    def mark_task_complete(self, task_id: str) -> Optional[Task]:
        """Mark a task as completed"""
        task = self.tasks.get(task_id)
        if not task:
            return None
            
        task.complete()
        self._save_tasks()
        return task 

    def summarize_the_day(self, tasks: list) -> str:
        return self.claude_service.summarize_the_day(tasks)
