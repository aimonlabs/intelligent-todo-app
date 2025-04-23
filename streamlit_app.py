import streamlit as st
import os
import time as time_module
from datetime import datetime, timedelta, time
import threading
import logging
import pytz
import re
from todo_agent import TodoAgent
from task_model import TaskStatus
from email_service import EmailService
from reminder_service import ReminderService
import json
import uuid
from typing import Dict, List, Union, Any, Optional

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create a lock for thread-safe operations
lock = threading.Lock()

# Pacific timezone
pacific_tz = pytz.timezone('America/Los_Angeles')

# Email validation regex
EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

class Task:
    def __init__(self, id: str, description: str, estimated_hours: float, 
                due_date: datetime, completed: bool = False, created_at: datetime = None,
                last_reminded_at: Optional[datetime] = None):
        self.id = id
        self.description = description
        self.estimated_hours = estimated_hours
        self.due_date = due_date
        self.completed = completed
        self.created_at = created_at if created_at else datetime.now(pacific_tz)
        self.last_reminded_at = last_reminded_at
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "estimated_hours": self.estimated_hours,
            "due_date": self.due_date.isoformat(),
            "completed": self.completed,
            "created_at": self.created_at.isoformat(),
            "last_reminded_at": self.last_reminded_at.isoformat() if self.last_reminded_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        return cls(
            id=data["id"],
            description=data["description"],
            estimated_hours=data["estimated_hours"],
            due_date=datetime.fromisoformat(data["due_date"]),
            completed=data["completed"],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_reminded_at=datetime.fromisoformat(data["last_reminded_at"]) if data.get("last_reminded_at") else None
        )

def initialize_app():
    """Initialize the application state"""
    if 'initialized' not in st.session_state:
        # Get API key from env or secrets
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        
        # Try to get from secrets if not in environment
        if not api_key:
            try:
                api_key = st.secrets.get("ANTHROPIC_API_KEY")
            except Exception:
                # No secrets file or key not found in secrets
                pass
                
        if not api_key:
            st.warning("Anthropic API key not provided. Please set ANTHROPIC_API_KEY environment variable for intelligent time estimation.")
        
        # Create the agent
        logger.info(f"Initializing TODO agent with storage at tasks.json")
        st.session_state.todo_agent = TodoAgent(storage_path="tasks.json", claude_api_key=api_key)
        
        # Set up email service
        st.session_state.email_service = EmailService()
        
        # Set up reminder service
        st.session_state.reminder_service = ReminderService(
            email_service=st.session_state.email_service,
            reminder_buffer_hours=24,
            logger=logger
        )
        
        # Set up reminder checking
        st.session_state.last_check_time = time_module.time()
        st.session_state.notifications = []
        st.session_state.last_email_sent = {}  # Track when last email was sent for each task
        
        # Flag to track state changes
        st.session_state.state_changed = False
        st.session_state.initialized = True

def email_setup_page():
    """Display the email setup page"""
    st.title("📧 Setup Email for Reminders")
    
    st.markdown("Before we begin, please provide your email address to receive task reminders.")
    
    with st.form("email_setup_form"):
        email = st.text_input("Your Email Address", value=st.session_state.user_email)
        submitted = st.form_submit_button("Continue to App")
        
        if submitted:
            # Validate email
            if not re.match(EMAIL_REGEX, email):
                st.error("Please enter a valid email address")
            else:
                st.session_state.user_email = email
                # Initialize email service and reminder agent
                try:
                    st.session_state.email_service = EmailService()
                    st.session_state.reminder_service = ReminderService(
                        email_service=st.session_state.email_service,
                        reminder_buffer_hours=24,
                        logger=logger
                    )
                    st.session_state.setup_complete = True
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to initialize email service: {str(e)}")

def handle_enter():
    """Handle Enter key in the task input"""
    if st.session_state.new_task.strip() and st.session_state.due_date:
        add_task()
    elif not st.session_state.new_task.strip():
        st.session_state.error_message = "Task description cannot be empty"
    elif not st.session_state.due_date:
        st.session_state.error_message = "Please select a due date"

def add_task():
    """Add a new task"""
    todo_description = st.session_state.new_task
    due_date = st.session_state.due_date
    
    if not todo_description:
        st.session_state.error_message = "Task description cannot be empty"
        return
    
    if not due_date:
        st.session_state.error_message = "Please select a due date"
        return
    
    # Use Claude to estimate time
    with st.spinner("Estimating task time with Claude..."):
        estimated_hours = st.session_state.todo_agent.estimate_task_time(todo_description)
    
    # Convert the date input to a datetime with time components in Pacific timezone
    # Set default time to 11:59 PM
    due_date_time = datetime.combine(due_date, time(23, 59))
    due_date_pacific = pacific_tz.localize(due_date_time)
    
    # Create the task with the Pacific timezone due date
    task = st.session_state.todo_agent.create_task(
        description=todo_description,
        due_date_str=due_date_pacific.isoformat(),
        estimated_hours=estimated_hours
    )
    
    # Clear the inputs
    st.session_state.new_task = ""
    st.session_state.due_date = None  # Clear the date after adding a task
    
    # Show success message via session state
    st.session_state.success_message = f"Added task with estimated time: {estimated_hours:.1f} hours, due on {due_date.strftime('%Y-%m-%d')} at 11:59 PM (Pacific)"
    
    # Set state changed flag
    st.session_state.state_changed = True

def delete_task(task_id):
    """Delete a task"""
    if st.session_state.todo_agent.delete_task(task_id):
        # Show success message via session state
        st.session_state.success_message = "Task deleted"
        # Set state changed flag
        st.session_state.state_changed = True
    else:
        st.session_state.error_message = "Failed to delete task"

def complete_task(task_id):
    """Mark a task as complete"""
    st.session_state.todo_agent.mark_task_complete(task_id)
    # Show success message via session state
    st.session_state.success_message = "Task marked as complete"
    # Set state changed flag
    st.session_state.state_changed = True

def start_task(task_id):
    """Mark a task as in progress - note: our new model only has completed/not completed, 
    so we're just updating the last updated timestamp"""
    task = st.session_state.todo_agent.get_task(task_id)
    if task:
        task.last_updated = datetime.now()
        st.session_state.todo_agent._save_tasks()
        
    # Show success message via session state
    st.session_state.success_message = "Task marked as in progress"
    # Set state changed flag
    st.session_state.state_changed = True

def edit_task(task_id):
    """Open a form to edit the task"""
    task = st.session_state.todo_agent.get_task(task_id)
    if not task:
        st.session_state.error_message = "Task not found"
        return
    
    st.session_state.editing_task = task
    st.session_state.editing = True
    st.session_state.state_changed = True

def save_edited_task():
    """Save the edited task"""
    task = st.session_state.editing_task
    
    # Get the updated description
    new_description = st.session_state.edit_description
    
    # If description changed, re-estimate time
    if new_description != task.description:
        with st.spinner("Re-estimating task time with Claude..."):
            estimated_hours = st.session_state.todo_agent.estimate_task_time(new_description)
        
        # Calculate new due date (current time + estimated time)
        due_date = datetime.now() + timedelta(hours=estimated_hours)
        
        # Update the task
        st.session_state.todo_agent.update_task(
            task_id=task.task_id,
            description=new_description,
            due_date_str=due_date.isoformat(),
            estimated_hours=estimated_hours
        )
    
    # Clear editing state
    st.session_state.editing = False
    st.session_state.editing_task = None
    
    # Success message
    st.session_state.success_message = "Task updated"
    
    # Set state changed flag
    st.session_state.state_changed = True

def cancel_edit():
    """Cancel the edit operation"""
    st.session_state.editing = False
    st.session_state.editing_task = None
    st.session_state.state_changed = True

def check_reminders():
    """Check if any tasks need reminders"""
    # Only check once every 30 seconds
    current_time = time_module.time()
    if current_time - st.session_state.last_check_time < 30:
        return
    
    st.session_state.last_check_time = current_time
    
    # Get all pending tasks
    tasks = st.session_state.todo_agent.list_tasks(status="pending")
    
    # Get current time in Pacific timezone to match the tasks
    now = datetime.now(pacific_tz)
    
    # Use our reminder service to check for due tasks
    reminder_service = st.session_state.reminder_service
    
    # Set the current user email if available
    if hasattr(st.session_state, 'user_email'):
        reminder_service.set_user_email(st.session_state.user_email)
    
    # Process reminders - this will check due tasks and send emails
    reminders_sent = reminder_service.process_reminders(tasks)
    
    if reminders_sent > 0:
        st.session_state.success_message = f"Sent {reminders_sent} task reminders"
        st.session_state.state_changed = True
    
    # Also check for tasks that should be added to in-app notifications
    for task in tasks:
        # Ensure task due date has timezone info
        if task.due_date.tzinfo is None:
            task_due_date = pacific_tz.localize(task.due_date)
        else:
            task_due_date = task.due_date
            
        # Calculate when to remind (due date minus estimated time)
        buffer_hours = max(4, task.estimated_hours * 1.5)  # At least 4 hours buffer or 1.5x estimated time
        remind_at = task_due_date - timedelta(hours=buffer_hours)
        
        # Ensure remind_at has timezone info for comparison
        if remind_at.tzinfo is None:
            remind_at = pacific_tz.localize(remind_at)
            
        # If it's time to remind in-app (or past time)
        if now >= remind_at:
            # Check if we haven't already notified for this task
            if task.task_id not in [n['id'] for n in st.session_state.notifications]:
                # Generate a message
                fun_message = f"Time to start on '{task.description}' - it's due soon!"
                
                # Add to notifications
                st.session_state.notifications.append({
                    'id': task.task_id,
                    'description': task.description,
                    'due_date': task_due_date,
                    'estimated_hours': task.estimated_hours,
                    'fun_message': fun_message
                })
                
                # Update status to in_progress
                with lock:
                    st.session_state.todo_agent.update_task(task.task_id, status="in_progress")
                
                # Set state changed flag if any notifications were added
                st.session_state.state_changed = True

def dismiss_notification(notification_id):
    """Dismiss a notification"""
    st.session_state.notifications = [n for n in st.session_state.notifications if n['id'] != notification_id]
    st.session_state.state_changed = True

def main():
    # Set page config
    st.set_page_config(
        page_title="Agentic TODO App",
        page_icon="✓",
        layout="wide"
    )
    
    # Initialize the app
    initialize_app()
    
    # If email setup not complete, show email page
    if not st.session_state.get('setup_complete', False):
        email_setup_page()
        return
    
    # Main app
    st.title("Agentic TODO App")
    st.markdown("An intelligent TODO list with Claude-powered time estimation")
    
    # Show user email with option to change
    with st.expander("Email Settings"):
        st.write(f"Reminders will be sent to: **{st.session_state.user_email}**")
        
        if st.button("Change Email"):
            st.session_state.setup_complete = False
            st.experimental_rerun()
    
    # Check for reminders
    check_reminders()
    
    # Display success/error messages if any
    if 'success_message' in st.session_state:
        st.success(st.session_state.success_message)
        del st.session_state.success_message
    
    if 'error_message' in st.session_state:
        st.error(st.session_state.error_message)
        del st.session_state.error_message
    
    # Display notifications at the top
    if st.session_state.notifications:
        st.subheader("Reminders")
        for idx, notification in enumerate(st.session_state.notifications):
            with st.container():
                cols = st.columns([3, 1, 1, 1])
                
                # Add fun message if available
                notification_text = f"**{notification['description']}**  \n"
                notification_text += f"Due: {notification['due_date'].strftime('%Y-%m-%d %H:%M')}  \n"
                notification_text += f"Estimated time: {notification['estimated_hours']:.1f} hours"
                
                if 'fun_message' in notification:
                    notification_text += f"\n\n*{notification['fun_message']}*"
                
                cols[0].markdown(notification_text)
                
                cols[1].button("Start", key=f"notif_start_{idx}_{notification['id'][:8]}", 
                              on_click=start_task, args=(notification['id'],))
                
                cols[2].button("Complete", key=f"notif_complete_{idx}_{notification['id'][:8]}", 
                              on_click=complete_task, args=(notification['id'],))
                
                cols[3].button("Dismiss", key=f"notif_dismiss_{idx}_{notification['id'][:8]}", 
                              on_click=dismiss_notification, args=(notification['id'],))
                
            st.divider()
    
    # Edit form (conditionally displayed)
    if st.session_state.get('editing', False) and st.session_state.get('editing_task'):
        task = st.session_state.editing_task
        st.subheader("Edit Task")
        
        # Input for task description
        st.text_input("Task Description", value=task.description, key="edit_description")
        
        # Current task details
        st.text(f"Current estimated time: {task.estimated_hours:.1f} hours")
        st.text(f"Current due date: {task.due_date.strftime('%Y-%m-%d %H:%M')}")
        
        # Save/Cancel buttons
        col1, col2 = st.columns(2)
        col1.button("Save", on_click=save_edited_task)
        col2.button("Cancel", on_click=cancel_edit)
        
        st.divider()
    

    st.subheader("📋 My Tasks (Grouped by Status)")

    # Grouped task sections (Asana style)
    task_groups = {
        "🟡 Pending": st.session_state.todo_agent.list_tasks(status="pending"),
        "🟢 In Progress": st.session_state.todo_agent.list_tasks(status="in_progress"),
        "✅ Completed": st.session_state.todo_agent.list_tasks(status="completed"),
    }

    for label, tasks in task_groups.items():
        with st.expander(label, expanded=True):
            if not tasks:
                st.info("No tasks in this section.")
                continue

            for idx, task in enumerate(tasks):
                with st.container():
                    cols = st.columns([4, 1, 1, 1, 1])
                    cols[0].markdown(
                        f"**{task.title}**  \n"
                        f"📅 Due: {task.due_date.strftime('%Y-%m-%d %H:%M')}  \n"
                        f"⏱️ Est: {task.estimated_hours:.1f} hrs"
                    )
                    task_id_short = task.task_id[:8]

                    # Edit
                    cols[1].button("✏️", key=f"edit_{label}_{idx}_{task_id_short}",
                                on_click=edit_task, args=(task.task_id,), help="Edit task")

                    # Complete
                    if not task.completed:
                        cols[2].button("✅", key=f"done_{label}_{idx}_{task_id_short}",
                                    on_click=complete_task, args=(task.task_id,), help="Mark complete")

                    # Start
                    if not task.completed:
                        cols[3].button("▶️", key=f"start_{label}_{idx}_{task_id_short}",
                                    on_click=start_task, args=(task.task_id,), help="Start task")

                    # Delete
                    cols[4].button("🗑️", key=f"delete_{label}_{idx}_{task_id_short}",
                                on_click=delete_task, args=(task.task_id,), help="Delete task")
                st.divider()

            # 2) Add-task slot at bottom of this section
            slot_key = f"show_add_{label}"
            if st.button("➕ Add a task…", key=f"toggle_{label}"):
                st.session_state[slot_key] = not st.session_state.get(slot_key, False)

            if st.session_state.get(slot_key, False):
                with st.form(key=f"form_{label}"):
                    new_desc = st.text_input("Task Description", key=f"desc_{label}")
                    new_date = st.date_input("Due Date", key=f"date_{label}", min_value=datetime.now(pacific_tz).date())
                    submit = st.form_submit_button("Submit")

                    if submit:
                        if not new_desc.strip():
                            st.error("Task description cannot be empty")
                        elif not new_date:
                            st.error("Please select a due date")
                        else:
                            due_dt = datetime.combine(new_date, time(23, 59))
                            due_pac = pacific_tz.localize(due_dt)

                            with st.spinner("Estimating time with Claude..."):
                                est_hours = st.session_state.todo_agent.estimate_task_time(new_desc)

                            st.session_state.todo_agent.create_task(
                                description=new_desc.strip(),
                                due_date_str=due_pac.isoformat(),
                                estimated_hours=est_hours
                            )

                            st.session_state.success_message = f"Added task with estimated time: {est_hours:.1f} hours"
                            st.session_state.state_changed = True
                            st.session_state[slot_key] = False
                            st.rerun()



    # Check if state has changed and rerun if needed
    if st.session_state.get('state_changed', False):
        st.session_state.state_changed = False
        st.rerun()

if __name__ == "__main__":
    # Initialize session state variables
    if 'new_task' not in st.session_state:
        st.session_state.new_task = ""
    
    if 'due_date' not in st.session_state:
        st.session_state.due_date = None
    
    if 'editing' not in st.session_state:
        st.session_state.editing = False
    
    if 'editing_task' not in st.session_state:
        st.session_state.editing_task = None
    
    if 'notifications' not in st.session_state:
        st.session_state.notifications = []
    
    if 'state_changed' not in st.session_state:
        st.session_state.state_changed = False
        
    if 'user_email' not in st.session_state:
        st.session_state.user_email = ""
        
    if 'setup_complete' not in st.session_state:
        st.session_state.setup_complete = False
        
    if 'email_validated' not in st.session_state:
        st.session_state.email_validated = False
        
    if 'last_email_sent' not in st.session_state:
        st.session_state.last_email_sent = {}
    
    main() 