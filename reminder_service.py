from datetime import datetime, timedelta
import threading
import time
import logging
from typing import Dict, List, Callable, Optional
from task_model import Task, TaskStatus
import random
from email_service import EmailService
import pytz

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ReminderService:
    """Service for managing and sending task reminders"""
    
    def __init__(
        self,
        email_service: EmailService,
        user_email: Optional[str] = None,
        reminder_buffer_hours: int = 24,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the reminder service
        
        Args:
            email_service: EmailService instance for sending reminders
            user_email: Default email to send reminders to
            reminder_buffer_hours: How many hours before due date to send reminders
            logger: Logger instance
        """
        self.email_service = email_service
        self.user_email = user_email
        self.reminder_buffer_hours = reminder_buffer_hours
        self.logger = logger or logging.getLogger(__name__)
        self.tasks = {}  # Task storage {task_id: task}
        
        # Threading setup
        self.stop_event = threading.Event()
        self.reminder_thread = None
        
        # Fun reminder messages to rotate through
        self.reminder_templates = [
            "⏰ Don't forget! Your task '{title}' is due {due_date_str}.",
            "👋 Hey there! Just a friendly reminder about '{title}' due on {due_date_str}.",
            "⚡ Time is ticking for '{title}' - it's due {due_date_str}!",
            "🚀 Ready to complete '{title}'? It's coming up on {due_date_str}.",
            "📝 Your to-do list is calling! '{title}' needs attention by {due_date_str}.",
            "🌟 You've got this! '{title}' is scheduled for completion by {due_date_str}.",
            "🔔 Reminder alert! Task '{title}' is due {due_date_str}."
        ]
        
        self.priority_indicators = {
            "high": "🔴 HIGH PRIORITY: ",
            "medium": "🟠 Medium Priority: ",
            "low": "🟢 Low Priority: "
        }
    
    def set_user_email(self, email: str) -> None:
        """Set the default user email for reminders"""
        self.user_email = email
        
    def check_due_tasks(self, tasks: List[Task]) -> List[Task]:
        """
        Find tasks that are due soon and need reminders
        
        Args:
            tasks: List of tasks to check
            
        Returns:
            List of tasks needing reminders
        """
        # Use UTC for consistency
        now = datetime.now(pytz.UTC)
        reminder_threshold = now + timedelta(hours=self.reminder_buffer_hours)
        
        due_tasks = []
        for task in tasks:
            # Skip completed tasks or tasks without due dates
            if task.completed or not task.due_date:
                continue
                
            # Handle timezone-aware and naive datetimes
            task_due_date = task.due_date
            if task_due_date.tzinfo is None:
                # Make naive datetime timezone-aware using UTC
                task_due_date = pytz.UTC.localize(task_due_date)
                
            # Check if the task is due within the reminder window
            if task_due_date <= reminder_threshold:
                # Check if we've already sent a reminder recently
                if task.last_reminded:
                    # Handle last_reminded timezone awareness too
                    last_reminded = task.last_reminded
                    if last_reminded.tzinfo is None:
                        last_reminded = pytz.UTC.localize(last_reminded)
                        
                    hours_since_reminder = (now - last_reminded).total_seconds() / 3600
                        
                    # Don't remind if we sent a reminder in the last 12 hours
                    if hours_since_reminder < 12:
                        continue
                        
                due_tasks.append(task)
                
        return due_tasks
    
    def _format_reminder_message(self, task: Task) -> Dict[str, str]:
        """Create a reminder message for a task"""
        # Format the due date for display
        due_date_str = "today"
        if task.due_date:
            # Make sure due_date is timezone-aware
            if task.due_date.tzinfo is None:
                due_date = pytz.UTC.localize(task.due_date)
            else:
                due_date = task.due_date
            
            now = datetime.now(pytz.UTC)
            if due_date.date() == now.date():
                due_date_str = "today"
            elif due_date.date() == (now + timedelta(days=1)).date():
                due_date_str = "tomorrow"
            else:
                due_date_str = due_date.strftime("%A, %B %d")
        
        # Choose a random template
        template = random.choice(self.reminder_templates)
        
        # Format the basic message
        message = template.format(title=task.title, due_date_str=due_date_str)
        
        # Add priority prefix if available
        if task.priority and task.priority.lower() in self.priority_indicators:
            message = self.priority_indicators[task.priority.lower()] + message
            
        # Create a more detailed HTML version
        html_message = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
            <h2>{message}</h2>
            
            <div style="margin: 15px 0;">
                {f"<p><strong>Description:</strong> {task.description}</p>" if task.description else ""}
                <p><strong>Due:</strong> {due_date_str}</p>
                {f"<p><strong>Priority:</strong> {task.priority}</p>" if task.priority else ""}
                {f"<p><strong>Estimated Time:</strong> {task.estimated_hours} hours</p>" if task.estimated_hours else ""}
            </div>
            
            <div style="margin-top: 20px; font-size: 0.9em; color: #666;">
                <p>This reminder was sent from your Todo App. Task ID: {task.task_id}</p>
            </div>
        </div>
        """
        
        return {
            "subject": f"Reminder: {task.title}",
            "body": message,
            "html_body": html_message
        }
    
    def send_reminder(self, task: Task, email: Optional[str] = None) -> bool:
        """
        Send a reminder email for a specific task
        
        Args:
            task: The task to send a reminder for
            email: Email to send to (uses default if not specified)
            
        Returns:
            bool: True if reminder was sent successfully
        """
        recipient = email or self.user_email
        
        if not recipient:
            self.logger.error("Cannot send reminder: No recipient email specified")
            return False
            
        # Create the reminder message
        message = self._format_reminder_message(task)
        
        # Send the email
        success = self.email_service.send_email(
            recipient_email=recipient,
            subject=message["subject"],
            body=message["html_body"],
            is_html=True
        )
        
        if success:
            # Update the last_reminded timestamp with a timezone-aware datetime
            if hasattr(task, 'update_last_reminded'):
                task.update_last_reminded()
            else:
                # Fallback if method doesn't exist
                task.last_reminded = datetime.now(pytz.UTC)
            
            self.logger.info(f"Reminder sent for task: {task.title}")
        
        return success
    
    def process_reminders(self, tasks: List[Task], email: Optional[str] = None) -> int:
        """
        Check and send reminders for all due tasks
        
        Args:
            tasks: List of tasks to check for reminders
            email: Optional email override
            
        Returns:
            int: Number of reminders sent
        """
        due_tasks = self.check_due_tasks(tasks)
        sent_count = 0
        
        for task in due_tasks:
            if self.send_reminder(task, email):
                sent_count += 1
                
        if sent_count > 0:
            self.logger.info(f"Sent {sent_count} task reminders")
            
        return sent_count

    def start(self, reminder_callback: Optional[Callable[[Task], None]] = None):
        """
        Start the reminder service in a background thread
        
        Args:
            reminder_callback: Optional callback function when a reminder triggers
        """
        if self.reminder_thread and self.reminder_thread.is_alive():
            self.logger.warning("Reminder service already running")
            return
            
        self.reminder_callback = reminder_callback or (lambda task: None)
        self.stop_event.clear()
        self.reminder_thread = threading.Thread(target=self._reminder_loop, daemon=True)
        self.reminder_thread.start()
        self.logger.info("Reminder service started")
    
    def stop(self):
        """Stop the reminder service"""
        if not self.reminder_thread or not self.reminder_thread.is_alive():
            self.logger.warning("Reminder service not running")
            return
            
        self.stop_event.set()
        self.reminder_thread.join(timeout=2.0)
        self.logger.info("Reminder service stopped")
    
    def add_task(self, task: Task):
        """Add or update a task in the reminder system"""
        self.tasks[task.task_id] = task
        self.logger.info(f"Task added to reminder service: {task.task_id}")
    
    def remove_task(self, task_id: str):
        """Remove a task from the reminder system"""
        if task_id in self.tasks:
            del self.tasks[task_id]
            self.logger.info(f"Task removed from reminder service: {task_id}")
    
    def _reminder_loop(self):
        """Background thread that checks for tasks needing reminders"""
        while not self.stop_event.is_set():
            now = datetime.now(pytz.UTC)
            
            for task_id, task in list(self.tasks.items()):
                # Skip completed tasks
                if task.completed:
                    continue
                
                # Skip tasks without due dates
                if not task.due_date:
                    continue
                    
                # Make sure due_date is timezone-aware
                due_date = task.due_date
                if due_date.tzinfo is None:
                    due_date = pytz.UTC.localize(due_date)
                
                # Calculate when to remind (due date minus estimated time)
                remind_at = due_date - timedelta(hours=task.estimated_hours or 1)
                
                # If it's time to remind (or past time)
                if now >= remind_at:
                    # Check if we haven't already sent a reminder recently
                    if task.last_reminded:
                        last_reminded = task.last_reminded
                        if last_reminded.tzinfo is None:
                            last_reminded = pytz.UTC.localize(last_reminded)
                        
                        hours_since_reminder = (now - last_reminded).total_seconds() / 3600
                        # Don't remind if we sent a reminder in the last 12 hours
                        if hours_since_reminder < 12:
                            continue
                    
                    self.logger.info(f"Sending reminder for task: {task.task_id}")
                    
                    # Send the email reminder
                    if self.user_email:
                        self.send_reminder(task)
                    
                    # Call the callback function if provided
                    self.reminder_callback(task)
            
            # Check every minute
            self.stop_event.wait(60) 