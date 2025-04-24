from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
import uuid
import pytz


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PAST_DUE = "past_due"

class Task:
    """Model representing a task in the todo list application"""
    
    def __init__(
        self,
        title: str,
        description: Optional[str] = None,
        due_date: Optional[datetime] = None,
        priority: Optional[str] = None,
        estimated_hours: Optional[float] = None,
        categories: Optional[List[str]] = None,
        task_id: Optional[str] = None
    ):
        """
        Initialize a new task
        
        Args:
            title: Task title
            description: Detailed description
            due_date: When the task is due
            priority: Priority level (high, medium, low)
            estimated_hours: Estimated time to complete in hours
            categories: List of categories this task belongs to
            task_id: Unique identifier (auto-generated if not provided)
        """
        self.title = title
        self.description = description
        
        # Ensure due_date has timezone if provided
        if due_date and due_date.tzinfo is None:
            self.due_date = pytz.UTC.localize(due_date)
        else:
            self.due_date = due_date
            
        self.priority = priority
        self.estimated_hours = estimated_hours
        self.categories = categories or []
        
        # Status tracking
        self.completed = False
        self.completed_date = None
        self.created_date = datetime.now(pytz.UTC)
        self.last_updated = self.created_date
        self.last_reminded = None
        
        # Generate a unique ID if not provided
        self.task_id = task_id or str(uuid.uuid4())
        
    def complete(self) -> None:
        """Mark the task as completed"""
        self.completed = True
        self.completed_date = datetime.now(pytz.UTC)
        self.last_updated = self.completed_date
        
    def uncomplete(self) -> None:
        """Mark the task as not completed"""
        self.completed = False
        self.completed_date = None
        self.last_updated = datetime.now(pytz.UTC)
        
    def update(self, **kwargs) -> None:
        """
        Update task properties
        
        Args:
            **kwargs: Key-value pairs of properties to update
        """
        allowed_fields = [
            'title', 'description', 'due_date', 
            'priority', 'estimated_hours', 'categories'
        ]
        
        for key, value in kwargs.items():
            if key in allowed_fields:
                # Handle due_date specially to ensure timezone awareness
                if key == 'due_date' and value and value.tzinfo is None:
                    value = pytz.UTC.localize(value)
                setattr(self, key, value)
                
        self.last_updated = datetime.now(pytz.UTC)
        
    def update_last_reminded(self) -> None:
        """Update the last reminded timestamp to now with timezone info"""
        self.last_reminded = datetime.now(pytz.UTC)
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert task to dictionary for serialization
        
        Returns:
            Dict representation of the task
        """
        return {
            'task_id': self.task_id,
            'title': self.title,
            'description': self.description,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'priority': self.priority,
            'estimated_hours': self.estimated_hours,
            'categories': self.categories,
            'completed': self.completed,
            'completed_date': self.completed_date.isoformat() if self.completed_date else None,
            'created_date': self.created_date.isoformat(),
            'last_updated': self.last_updated.isoformat(),
            'last_reminded': self.last_reminded.isoformat() if self.last_reminded else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """
        Create a Task instance from a dictionary
        
        Args:
            data: Dictionary containing task data
            
        Returns:
            Task instance
        """
        # Create a new task with the basic properties
        task = cls(
            title=data['title'],
            description=data.get('description'),
            priority=data.get('priority'),
            estimated_hours=data.get('estimated_hours'),
            categories=data.get('categories', []),
            task_id=data.get('task_id')
        )
        
        # Set date fields that need parsing
        if data.get('due_date'):
            task.due_date = datetime.fromisoformat(data['due_date'])
            
        if data.get('completed'):
            task.completed = data['completed']
            
        if data.get('completed_date'):
            task.completed_date = datetime.fromisoformat(data['completed_date'])
            
        if data.get('created_date'):
            task.created_date = datetime.fromisoformat(data['created_date'])
            
        if data.get('last_updated'):
            task.last_updated = datetime.fromisoformat(data['last_updated'])
            
        if data.get('last_reminded'):
            task.last_reminded = datetime.fromisoformat(data['last_reminded'])
            
        return task
        
    def __str__(self) -> str:
        """String representation of the task"""
        status = "✓" if self.completed else "□"
        due_str = f", due: {self.due_date.strftime('%Y-%m-%d')}" if self.due_date else ""
        return f"[{status}] {self.title}{due_str}" 