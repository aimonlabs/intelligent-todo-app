import logging
import random
from datetime import datetime, timedelta
from email_service import EmailService

class ReminderAgent:
    """Agent responsible for managing and sending reminders for upcoming tasks"""
    
    def __init__(self, email_service=None):
        """
        Initialize the reminder agent
        
        Args:
            email_service: An EmailService instance for sending emails
        """
        self.email_service = email_service or EmailService()
        self.user_email = None
        
    def set_user_email(self, email):
        """Set the user's email address for notifications"""
        self.user_email = email
        
    def check_and_send_reminders(self, tasks):
        """
        Check for tasks that need reminders and send them
        
        Args:
            tasks: List of Task objects to check
        
        Returns:
            List of task IDs that had reminders sent
        """
        if not self.user_email:
            logging.warning("No user email set. Skipping reminders.")
            return []
            
        now = datetime.now()
        reminded_tasks = []
        
        for task in tasks:
            # Skip tasks without due dates
            if not task.due_date:
                continue
                
            # Calculate time until due
            time_until_due = task.due_date - now
            
            # Send reminder if task is due within 24 hours and has sufficient
            # time to complete based on estimated hours
            buffer_hours = max(4, task.estimated_hours * 1.5)  # At least 4 hours buffer or 1.5x estimated time
            buffer = timedelta(hours=buffer_hours)
            
            if 0 < time_until_due <= buffer:
                self._send_task_reminder(task)
                reminded_tasks.append(task.id)
                
        return reminded_tasks
    
    def _send_task_reminder(self, task):
        """
        Send a reminder for a specific task
        
        Args:
            task: The Task object to send a reminder for
        """
        fun_message = self._generate_fun_message(task)
        
        try:
            self.email_service.send_reminder(
                to_email=self.user_email,
                subject=f"Reminder: {task.description[:40]}...",
                task_description=task.description,
                due_date=task.due_date,
                estimated_hours=task.estimated_hours,
                fun_message=fun_message
            )
            logging.info(f"Sent reminder for task: {task.id}")
        except Exception as e:
            logging.error(f"Failed to send reminder for task {task.id}: {str(e)}")
    
    def _generate_fun_message(self, task):
        """
        Generate a fun, motivational message for the reminder
        
        Args:
            task: The Task object to generate a message for
            
        Returns:
            A string containing a fun reminder message
        """
        # List of fun reminder templates
        templates = [
            "Time to conquer this task! Your future self will thank you. 💪",
            "Hey there! This task won't complete itself. Let's make it happen! ✨",
            "Productivity mode: Activated! You've got this task in the bag. 🚀",
            f"Imagine how good it will feel to check off '{task.description}' from your list!",
            "Remember: Procrastination is just a fancy word for self-sabotage. You deserve better!",
            "Coffee ☕ + You 👤 + This task = Success! Let's do this!",
            f"This task is waving at you and saying 'Hey, don't forget about me!'",
            "Tick tock! Time is running, but you're faster. Prove it by completing this task!",
            "Your to-do list believes in you, even on days when you don't believe in yourself.",
            "Success isn't always about greatness. It's about consistency. Let's be consistent!"
        ]
        
        return random.choice(templates) 