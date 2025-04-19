from datetime import datetime
import uuid

class Task:
    """Represents a task with description, due date, and time estimate"""
    
    def __init__(self, description, due_date=None, estimated_hours=1.0, completed=False, id=None):
        """
        Initialize a new task
        
        Args:
            description (str): Task description
            due_date (datetime, optional): When the task is due
            estimated_hours (float, optional): Estimated hours to complete
            completed (bool, optional): Whether task is completed
            id (str, optional): Task ID, auto-generated if not provided
        """
        self.id = id or str(uuid.uuid4())
        self.description = description
        self.due_date = due_date
        self.estimated_hours = estimated_hours
        self.completed = completed
        self.created_at = datetime.now()
        self.last_reminded = None
        
    def mark_completed(self):
        """Mark the task as completed"""
        self.completed = True
        
    def mark_reminded(self):
        """Update the last reminded timestamp"""
        self.last_reminded = datetime.now()
        
    def to_dict(self):
        """Convert task to dictionary for serialization"""
        return {
            'id': self.id,
            'description': self.description,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'estimated_hours': self.estimated_hours,
            'completed': self.completed,
            'created_at': self.created_at.isoformat(),
            'last_reminded': self.last_reminded.isoformat() if self.last_reminded else None
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create a Task instance from dictionary data"""
        task = cls(
            description=data['description'],
            id=data['id']
        )
        
        if data.get('due_date'):
            task.due_date = datetime.fromisoformat(data['due_date'])
            
        task.estimated_hours = data.get('estimated_hours', 1.0)
        task.completed = data.get('completed', False)
        task.created_at = datetime.fromisoformat(data['created_at']) 
        
        if data.get('last_reminded'):
            task.last_reminded = datetime.fromisoformat(data['last_reminded'])
            
        return task 