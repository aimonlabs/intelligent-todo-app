import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime, timedelta
from typing import Callable, Optional
import threading
import time

from todo_agent import TodoAgent
from task_model import Task, TaskStatus
from reminder_service import ReminderService


class TodoAppUI:
    def __init__(self, root: tk.Tk, todo_agent: TodoAgent):
        self.root = root
        self.todo_agent = todo_agent
        
        # Set up reminder service
        self.reminder_service = ReminderService(self.show_reminder)
        
        # Set up UI components
        self._setup_ui()
        
        # Load tasks at startup
        self.refresh_task_list()
        
        # Start reminder service
        self.reminder_service.start()
        
        # Register cleanup on window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def _setup_ui(self):
        """Set up the UI components"""
        self.root.title("Agentic TODO App")
        self.root.geometry("800x600")
        
        # Create main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Task list
        task_frame = ttk.LabelFrame(main_frame, text="Tasks", padding="10")
        task_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Treeview for tasks
        columns = ("id", "description", "due_date", "estimated_hours", "status")
        self.task_tree = ttk.Treeview(task_frame, columns=columns, show="headings")
        
        # Define column headings
        self.task_tree.heading("id", text="ID")
        self.task_tree.heading("description", text="Description")
        self.task_tree.heading("due_date", text="Due Date")
        self.task_tree.heading("estimated_hours", text="Est. Hours")
        self.task_tree.heading("status", text="Status")
        
        # Set column widths
        self.task_tree.column("id", width=80)
        self.task_tree.column("description", width=300)
        self.task_tree.column("due_date", width=150)
        self.task_tree.column("estimated_hours", width=80)
        self.task_tree.column("status", width=100)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(task_frame, orient=tk.VERTICAL, command=self.task_tree.yview)
        self.task_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.task_tree.pack(fill=tk.BOTH, expand=True)
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        # Add buttons
        ttk.Button(button_frame, text="Add Task", command=self.add_task).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Edit Task", command=self.edit_task).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Delete Task", command=self.delete_task).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Mark Complete", command=self.mark_complete).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Refresh", command=self.refresh_task_list).pack(side=tk.LEFT, padx=5)
        
        # Filter frame
        filter_frame = ttk.Frame(main_frame)
        filter_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(filter_frame, text="Filter by status:").pack(side=tk.LEFT, padx=5)
        
        # Status filter dropdown
        self.status_var = tk.StringVar(value="All")
        status_dropdown = ttk.Combobox(filter_frame, textvariable=self.status_var, values=["All", "pending", "in_progress", "completed"])
        status_dropdown.pack(side=tk.LEFT, padx=5)
        status_dropdown.bind("<<ComboboxSelected>>", lambda _: self.refresh_task_list())
    
    def refresh_task_list(self):
        """Refresh the task list display"""
        # Clear existing items
        for item in self.task_tree.get_children():
            self.task_tree.delete(item)
        
        # Get status filter
        status_filter = self.status_var.get()
        if status_filter == "All":
            tasks = self.todo_agent.list_tasks()
        else:
            tasks = self.todo_agent.list_tasks(status=status_filter)
        
        # Update reminder service with tasks
        for task in tasks:
            self.reminder_service.add_task(task)
        
        # Add tasks to tree
        for task in tasks:
            due_date_str = task.due_date.strftime("%Y-%m-%d %H:%M")
            
            # Set row color based on status
            tags = (task.status.value,)
            
            self.task_tree.insert("", tk.END, values=(
                task.id[:8],  # Show first 8 chars of UUID
                task.description,
                due_date_str,
                f"{task.estimated_hours:.1f}",
                task.status.value
            ), tags=tags)
        
        # Configure tag colors
        self.task_tree.tag_configure("pending", background="#FFFFCC")
        self.task_tree.tag_configure("in_progress", background="#CCFFCC")
        self.task_tree.tag_configure("completed", background="#CCCCCC")
    
    def add_task(self):
        """Open dialog to add a new task"""
        # Create a dialog window
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Task")
        dialog.geometry("400x250")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Description
        ttk.Label(dialog, text="Description:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        description_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=description_var, width=40).grid(row=0, column=1, padx=10, pady=5)
        
        # Due date
        ttk.Label(dialog, text="Due Date:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        
        # Create frame for date/time inputs
        date_frame = ttk.Frame(dialog)
        date_frame.grid(row=1, column=1, padx=10, pady=5, sticky=tk.W)
        
        # Default to tomorrow
        tomorrow = datetime.now() + timedelta(days=1)
        
        # Date components
        year_var = tk.StringVar(value=str(tomorrow.year))
        month_var = tk.StringVar(value=str(tomorrow.month))
        day_var = tk.StringVar(value=str(tomorrow.day))
        hour_var = tk.StringVar(value="18")
        minute_var = tk.StringVar(value="0")
        
        ttk.Spinbox(date_frame, from_=2023, to=2030, textvariable=year_var, width=5).pack(side=tk.LEFT, padx=2)
        ttk.Label(date_frame, text="-").pack(side=tk.LEFT)
        ttk.Spinbox(date_frame, from_=1, to=12, textvariable=month_var, width=3).pack(side=tk.LEFT, padx=2)
        ttk.Label(date_frame, text="-").pack(side=tk.LEFT)
        ttk.Spinbox(date_frame, from_=1, to=31, textvariable=day_var, width=3).pack(side=tk.LEFT, padx=2)
        ttk.Label(date_frame, text="  ").pack(side=tk.LEFT)
        ttk.Spinbox(date_frame, from_=0, to=23, textvariable=hour_var, width=3).pack(side=tk.LEFT, padx=2)
        ttk.Label(date_frame, text=":").pack(side=tk.LEFT)
        ttk.Spinbox(date_frame, from_=0, to=59, textvariable=minute_var, width=3).pack(side=tk.LEFT, padx=2)
        
        # Estimated hours
        ttk.Label(dialog, text="Estimated Hours:").grid(row=2, column=0, sticky=tk.W, padx=10, pady=5)
        est_hours_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=est_hours_var, width=10).grid(row=2, column=1, padx=10, pady=5, sticky=tk.W)
        
        # Auto-estimate checkbox
        auto_estimate_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(dialog, text="Auto-estimate with Claude", variable=auto_estimate_var).grid(row=3, column=1, padx=10, pady=5, sticky=tk.W)
        
        # Status
        ttk.Label(dialog, text="Status:").grid(row=4, column=0, sticky=tk.W, padx=10, pady=5)
        status_var = tk.StringVar(value="pending")
        ttk.Combobox(dialog, textvariable=status_var, values=["pending", "in_progress", "completed"]).grid(row=4, column=1, padx=10, pady=5, sticky=tk.W)
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=5, column=0, columnspan=2, pady=15)
        
        def on_submit():
            try:
                description = description_var.get().strip()
                if not description:
                    messagebox.showerror("Error", "Description cannot be empty")
                    return
                
                # Construct due date
                due_date = datetime(
                    year=int(year_var.get()),
                    month=int(month_var.get()),
                    day=int(day_var.get()),
                    hour=int(hour_var.get()),
                    minute=int(minute_var.get())
                )
                
                # Get or estimate hours
                estimated_hours = None
                if not auto_estimate_var.get():
                    if est_hours_var.get().strip():
                        estimated_hours = float(est_hours_var.get())
                
                # Create task
                task = self.todo_agent.create_task(
                    description=description,
                    due_date_str=due_date.isoformat(),
                    estimated_hours=estimated_hours
                )
                
                # Add to reminder service
                self.reminder_service.add_task(task)
                
                dialog.destroy()
                self.refresh_task_list()
                
                # Show estimation if it was auto-estimated
                if auto_estimate_var.get():
                    messagebox.showinfo("Time Estimation", 
                                       f"Claude estimated this task will take {task.estimated_hours:.1f} hours to complete.")
            
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create task: {e}")
        
        ttk.Button(button_frame, text="Submit", command=on_submit).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def edit_task(self):
        """Edit the selected task"""
        # Get selected task
        selection = self.task_tree.selection()
        if not selection:
            messagebox.showinfo("Info", "Please select a task to edit")
            return
            
        task_id = self.task_tree.item(selection[0], "values")[0]
        
        # Find the full task ID
        for task_full_id, task in self.todo_agent.tasks.items():
            if task_full_id.startswith(task_id):
                task_id = task_full_id
                break
        
        task = self.todo_agent.get_task(task_id)
        if not task:
            messagebox.showerror("Error", f"Task with ID {task_id} not found")
            return
        
        # Create a dialog window similar to add_task
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Task")
        dialog.geometry("400x250")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Description
        ttk.Label(dialog, text="Description:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        description_var = tk.StringVar(value=task.description)
        ttk.Entry(dialog, textvariable=description_var, width=40).grid(row=0, column=1, padx=10, pady=5)
        
        # Due date
        ttk.Label(dialog, text="Due Date:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        
        # Create frame for date/time inputs
        date_frame = ttk.Frame(dialog)
        date_frame.grid(row=1, column=1, padx=10, pady=5, sticky=tk.W)
        
        # Date components
        year_var = tk.StringVar(value=str(task.due_date.year))
        month_var = tk.StringVar(value=str(task.due_date.month))
        day_var = tk.StringVar(value=str(task.due_date.day))
        hour_var = tk.StringVar(value=str(task.due_date.hour))
        minute_var = tk.StringVar(value=str(task.due_date.minute))
        
        ttk.Spinbox(date_frame, from_=2023, to=2030, textvariable=year_var, width=5).pack(side=tk.LEFT, padx=2)
        ttk.Label(date_frame, text="-").pack(side=tk.LEFT)
        ttk.Spinbox(date_frame, from_=1, to=12, textvariable=month_var, width=3).pack(side=tk.LEFT, padx=2)
        ttk.Label(date_frame, text="-").pack(side=tk.LEFT)
        ttk.Spinbox(date_frame, from_=1, to=31, textvariable=day_var, width=3).pack(side=tk.LEFT, padx=2)
        ttk.Label(date_frame, text="  ").pack(side=tk.LEFT)
        ttk.Spinbox(date_frame, from_=0, to=23, textvariable=hour_var, width=3).pack(side=tk.LEFT, padx=2)
        ttk.Label(date_frame, text=":").pack(side=tk.LEFT)
        ttk.Spinbox(date_frame, from_=0, to=59, textvariable=minute_var, width=3).pack(side=tk.LEFT, padx=2)
        
        # Estimated hours
        ttk.Label(dialog, text="Estimated Hours:").grid(row=2, column=0, sticky=tk.W, padx=10, pady=5)
        est_hours_var = tk.StringVar(value=str(task.estimated_hours))
        ttk.Entry(dialog, textvariable=est_hours_var, width=10).grid(row=2, column=1, padx=10, pady=5, sticky=tk.W)
        
        # Status
        ttk.Label(dialog, text="Status:").grid(row=3, column=0, sticky=tk.W, padx=10, pady=5)
        status_var = tk.StringVar(value=task.status.value)
        ttk.Combobox(dialog, textvariable=status_var, values=["pending", "in_progress", "completed"]).grid(row=3, column=1, padx=10, pady=5, sticky=tk.W)
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=4, column=0, columnspan=2, pady=15)
        
        def on_submit():
            try:
                description = description_var.get().strip()
                if not description:
                    messagebox.showerror("Error", "Description cannot be empty")
                    return
                
                # Construct due date
                due_date = datetime(
                    year=int(year_var.get()),
                    month=int(month_var.get()),
                    day=int(day_var.get()),
                    hour=int(hour_var.get()),
                    minute=int(minute_var.get())
                )
                
                # Get hours
                estimated_hours = float(est_hours_var.get())
                
                # Update task
                updated_task = self.todo_agent.update_task(
                    task_id=task_id,
                    description=description,
                    due_date_str=due_date.isoformat(),
                    estimated_hours=estimated_hours,
                    status=status_var.get()
                )
                
                # Update reminder service
                self.reminder_service.add_task(updated_task)
                
                dialog.destroy()
                self.refresh_task_list()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update task: {e}")
        
        ttk.Button(button_frame, text="Submit", command=on_submit).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def delete_task(self):
        """Delete the selected task"""
        selection = self.task_tree.selection()
        if not selection:
            messagebox.showinfo("Info", "Please select a task to delete")
            return
            
        task_id = self.task_tree.item(selection[0], "values")[0]
        
        # Find the full task ID
        for task_full_id, task in self.todo_agent.tasks.items():
            if task_full_id.startswith(task_id):
                task_id = task_full_id
                break
        
        if messagebox.askyesno("Confirm", "Are you sure you want to delete this task?"):
            success = self.todo_agent.delete_task(task_id)
            if success:
                self.reminder_service.remove_task(task_id)
                self.refresh_task_list()
            else:
                messagebox.showerror("Error", f"Failed to delete task with ID {task_id}")
    
    def mark_complete(self):
        """Mark the selected task as complete"""
        selection = self.task_tree.selection()
        if not selection:
            messagebox.showinfo("Info", "Please select a task to mark as complete")
            return
            
        task_id = self.task_tree.item(selection[0], "values")[0]
        
        # Find the full task ID
        for task_full_id, task in self.todo_agent.tasks.items():
            if task_full_id.startswith(task_id):
                task_id = task_full_id
                break
        
        updated_task = self.todo_agent.mark_task_complete(task_id)
        if updated_task:
            self.reminder_service.add_task(updated_task)
            self.refresh_task_list()
        else:
            messagebox.showerror("Error", f"Failed to update task with ID {task_id}")
    
    def show_reminder(self, task: Task):
        """Show a reminder for a task"""
        # Schedule UI update in main thread
        self.root.after(0, lambda: self._show_reminder_dialog(task))
    
    def _show_reminder_dialog(self, task: Task):
        """Show reminder dialog in the main thread"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Task Reminder")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.attributes("-topmost", True)
        dialog.grab_set()
        
        # Make it stand out
        dialog.configure(bg="#FFE0E0")
        
        # Content
        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Time to start working on:", font=("Arial", 12)).pack(pady=5)
        ttk.Label(frame, text=task.description, font=("Arial", 14, "bold")).pack(pady=5)
        
        due_date_str = task.due_date.strftime("%Y-%m-%d %H:%M")
        ttk.Label(frame, text=f"Due: {due_date_str}").pack(pady=5)
        ttk.Label(frame, text=f"Estimated time: {task.estimated_hours:.1f} hours").pack(pady=5)
        
        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Mark as In Progress", 
                  command=lambda: self._update_reminder_task(dialog, task, "in_progress")).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Mark as Complete", 
                  command=lambda: self._update_reminder_task(dialog, task, "completed")).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Dismiss", 
                  command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def _update_reminder_task(self, dialog, task: Task, status: str):
        """Update task status from reminder dialog"""
        self.todo_agent.update_task(task_id=task.id, status=status)
        dialog.destroy()
        self.refresh_task_list()
    
    def on_close(self):
        """Clean up before closing the application"""
        self.reminder_service.stop()
        self.root.destroy() 