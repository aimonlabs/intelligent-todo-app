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
        logger.info(f"Initializing To-Do agent with storage at tasks.json")
        st.session_state.todo_agent = TodoAgent(storage_path="tasks.json", claude_api_key=api_key)
    
        # Flag to track state changes
        st.session_state.state_changed = False
        
        ## Expire tasks once per reload
        if 'overdue_checked' not in st.session_state:
            st.session_state.overdue_checked = False

        st.session_state.initialized = True

def handle_enter():
    """Handle Enter key in the task input"""
    if st.session_state.new_task.strip() and st.session_state.due_date:
        add_task()
    elif not st.session_state.new_task.strip():
        st.session_state.error_message = "Task description cannot be empty"
    elif not st.session_state.due_date:
        st.session_state.error_message = "Please select a due date"

def overdue_tasks():
    """Move overdue uncompleted tasks to past_due."""
    now = datetime.now(pacific_tz)
    past_due = 0
    for task in st.session_state.todo_agent.list_tasks(status="in_progress"):
        if task.due_date < now and not task.completed:
            st.session_state.todo_agent.update_task(task.task_id, status="past_due")
            past_due += 1
    if past_due:
        st.success(f"{past_due} task(s) moved to Past Due.")

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
    estimated_hours=estimated_hours,
    status="in_progress"  # explicitly set the initial status
    )

    # Clear the inputs
    st.session_state.new_task = ""
    st.session_state.due_date = None  # Clear the date after adding a task
    
    # Show success message via session state
    st.session_state.success_message = f"Added task with estimated time: {estimated_hours:.1f} hours, due on {due_date.strftime('%Y-%m-%d')} at 11:59 PM (Pacific)"
    
    # Set state changed flag
    st.session_state.state_changed = True

    ## Force summary
    st.session_state.force_summary_refresh = True
    # st.rerun()

def delete_task(task_id):
    """Delete a task"""
    if st.session_state.todo_agent.delete_task(task_id):
        # Show success message via session state
        st.session_state.success_message = "Task deleted"
        # Set state changed flag
        st.session_state.state_changed = True
        ## Force summary
        st.session_state.force_summary_refresh = True
        # st.rerun()
    else:
        st.session_state.error_message = "Failed to delete task"

def complete_task(task_id):
    """Mark a task as complete"""
    st.session_state.todo_agent.mark_task_complete(task_id)
    # Show success message via session state
    st.session_state.success_message = "Task marked as complete"
    # Set state changed flag
    st.session_state.state_changed = True

    ## Force summary
    st.session_state.force_summary_refresh = True
    # st.rerun()

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
    
    # New values from form
    new_description = st.session_state.edit_description
    new_due_date = datetime.combine(st.session_state.edit_due_date, time(23, 59))
    new_due_date = pacific_tz.localize(new_due_date)

    now = datetime.now(pacific_tz)

    # Estimate new time if description changed
    if new_description != task.description:
        with st.spinner("Re-estimating task time with Claude..."):
            estimated_hours = st.session_state.todo_agent.estimate_task_time(new_description)
    else:
        estimated_hours = task.estimated_hours

    # 👇 Derive status based on due date
    if task.completed:
        new_status = "completed"
    elif new_due_date < now:
        new_status = "past_due"
    else:
        new_status = "in_progress"

    # Update the task
    st.session_state.todo_agent.update_task(
        task_id=task.task_id,
        description=new_description,
        due_date_str=new_due_date.isoformat(),
        estimated_hours=estimated_hours,
        status=new_status
    )

    # Clean up
    st.session_state.editing = False
    st.session_state.editing_task = None
    st.session_state.success_message = "Task updated"
    st.session_state.state_changed = True
    st.session_state.force_summary_refresh = True
    # st.rerun()

def cancel_edit():
    """Cancel the edit operation"""
    st.session_state.editing = False
    st.session_state.editing_task = None
    st.session_state.state_changed = True

def dismiss_notification(notification_id):
    """Dismiss a notification"""
    st.session_state.notifications = [n for n in st.session_state.notifications if n['id'] != notification_id]
    st.session_state.state_changed = True

def show_daily_summary():
    today = datetime.now(pacific_tz).date()
    todays_tasks = [
        t for t in st.session_state.todo_agent.list_tasks(status="in_progress")
        if t.due_date.date() == today and not t.completed
    ]
    
    if todays_tasks:
        total_hours = sum(t.estimated_hours or 0 for t in todays_tasks)
        # st.subheader("🗓️ Overview for the day")
        st.markdown(f"You have **{len(todays_tasks)}** task(s) today totaling **~{total_hours:.1f} hrs**.")
        
        cached_date = st.session_state.get("summary_date")
        cached_summary = st.session_state.get("summary_text")

        if cached_date != today or st.session_state.get("force_summary_refresh", False):
            with st.spinner("Summarizing today's workload..."):
                try:
                    summary = st.session_state.todo_agent.summarize_the_day(todays_tasks)
                except Exception:
                    summary = "⚠️ Could not generate summary."
            st.session_state.summary_date = today
            st.session_state.summary_text = summary
            st.session_state.force_summary_refresh = False
        else:
            summary = cached_summary

        st.markdown("📘 **Overview for the day**")
        st.info(summary)
    else:
        st.info("🎉 No tasks scheduled for today. Enjoy your time!")

def main():
    # Set page config
    st.set_page_config(
        page_title="Agentic To-Do App",
        page_icon="✓",
        layout="wide"
    )
    
    # Initialize the app
    initialize_app()

    # Main app
    st.title("Agentic To-Do App")
    st.markdown("An intelligent To-Do list with Claude-powered time estimation")
   
    summary_container = st.container()

    # Expire missed tasks
    if not st.session_state.overdue_checked:
        overdue_tasks()
        st.session_state.overdue_checked = True

    # Display success/error messages if any
    if 'success_message' in st.session_state:
        st.success(st.session_state.success_message)
        del st.session_state.success_message
    
    if 'error_message' in st.session_state:
        st.error(st.session_state.error_message)
        del st.session_state.error_message
    
    # Edit form (conditionally displayed)
    if st.session_state.get('editing', False) and st.session_state.get('editing_task'):
        task = st.session_state.editing_task
        st.subheader("Edit Task")
        
        # Input for task description
        st.text_input("Task Description", value=task.description, key="edit_description")
        
        current_date = datetime.now(pacific_tz).date()
        st.date_input(
            "Due Date",
            value=task.due_date.date(), 
            min_value=min(current_date, task.due_date.date()),
            key="edit_due_date"
        )

        # Current task details
        st.text(f"Current estimated time: {task.estimated_hours:.1f} hours")
        st.text(f"Original due date: {task.due_date.strftime('%Y-%m-%d %H:%M')}")
        
        # Save/Cancel buttons
        col1, col2 = st.columns(2)
        col1.button("Save", on_click=save_edited_task)
        col2.button("Cancel", on_click=cancel_edit)
        
        st.divider()
    
    st.subheader("📋 My Tasks")

    # ——— Task Category Navbar ———
    task_category = st.radio("Choose Task Category:",
                            ["🟢 In Progress", "✅ Completed", "🟡 Past Due"],
                            horizontal=True,
                        )

    status_map = {
    "🟢 In Progress": "in_progress",
    "✅ Completed":   "completed",
    "🟡 Past Due":    "past_due"
    }

    selected_status = status_map[task_category]

    if selected_status == "in_progress":
        tasks = [
            t for t in st.session_state.todo_agent.list_tasks(status="in_progress")
            if t.due_date >= datetime.now(pacific_tz)
        ]
    else:
        tasks = st.session_state.todo_agent.list_tasks(status=selected_status)
    
    tasks.sort(key=lambda x: x.created_date, reverse=True)

    with st.expander(task_category, expanded=True):
        if not tasks:
            st.info("No tasks in this section.")
        for idx, task in enumerate(tasks):
            cols = st.columns([4, 1, 1, 1])  # drop the "Start" column
            cols[0].markdown(
                f"**{task.description}**  \n"
                f"📅 {task.due_date.strftime('%Y-%m-%d %H:%M')}  \n"
                f"⏱️ {task.estimated_hours:.1f} hrs"
            )
            # Edit button
            cols[1].button(
                "✏️",
                key=f"edit_{selected_status}_{idx}",
                on_click=edit_task,
                args=(task.task_id,),
                help="Edit task"
            )
            # Complete button (only if not past_due and not already done)
            if selected_status != "past_due" and not task.completed:
                cols[2].button(
                    "✅",
                    key=f"done_{selected_status}_{idx}",
                    on_click=complete_task,
                    args=(task.task_id,),
                    help="Mark complete"
                )
            # Delete button in last column
            cols[3].button(
                "🗑️",
                key=f"del_{selected_status}_{idx}",
                on_click=delete_task,
                args=(task.task_id,),
                help="Delete task"
            )
            st.divider()

        # ——— Add New Task Form ———
        if selected_status != "past_due":
            slot = f"show_add_{selected_status}"
            if st.button("➕ Add a task…", key=f"toggle_{selected_status}"):
                st.session_state[slot] = not st.session_state.get(slot, False)
            if st.session_state.get(slot, False):
                with st.form(key=f"form_{selected_status}"):
                    nd = st.text_input("Task Description", key=f"desc_{selected_status}")
                    dd = st.date_input(
                        "Due Date",
                        key=f"date_{selected_status}",
                        min_value=datetime.now(pacific_tz).date()
                    )
                    ok = st.form_submit_button("Submit")
                    if ok:
                        dt = datetime.combine(dd, time(23, 59))
                        dt_p = pacific_tz.localize(dt)
                        with st.spinner("Estimating time…"):
                            hrs = st.session_state.todo_agent.estimate_task_time(nd)
                        st.session_state.todo_agent.create_task(
                            description=nd.strip(),
                            due_date_str=dt_p.isoformat(),
                            estimated_hours=hrs
                        )
                        st.session_state.success_message = f"Added: {hrs:.1f} hrs"
                        st.session_state.state_changed = True
                        st.session_state[slot] = False

                        ## Force summary
                        st.session_state.force_summary_refresh = True
                        # st.rerun()

    # Daily summary
    with summary_container:
        show_daily_summary()

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
        
    if 'setup_complete' not in st.session_state:
        st.session_state.setup_complete = False
    
    main() 