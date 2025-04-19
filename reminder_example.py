#!/usr/bin/env python3
"""
Example script showing how to use the ReminderService to send email reminders for tasks
"""

import logging
import time
from datetime import datetime, timedelta
import os

from task_model import Task
from email_service import EmailService
from reminder_service import ReminderService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reminder_callback(task):
    """Called when a reminder is triggered"""
    logger.info(f"⏰ REMINDER CALLBACK: Task '{task.title}' is due soon!")

def main():
    # Check if email credentials are set
    if not os.environ.get("EMAIL_SENDER") or not os.environ.get("EMAIL_PASSWORD"):
        logger.warning(
            "Email credentials not set. Please set EMAIL_SENDER and EMAIL_PASSWORD "
            "environment variables to enable sending emails."
        )

    # Create an email service
    email_service = EmailService()
    
    # Create a reminder service with 1 hour reminder buffer
    reminder_service = ReminderService(
        email_service=email_service,
        reminder_buffer_hours=1
    )
    
    # Set the email to send reminders to
    user_email = os.environ.get("USER_EMAIL")
    if user_email:
        reminder_service.set_user_email(user_email)
        logger.info(f"Reminders will be sent to: {user_email}")
    else:
        logger.warning("No USER_EMAIL environment variable set. Reminders will not be sent.")
    
    # Create a task due in 30 minutes
    now = datetime.now()
    task1 = Task(
        title="Finish project proposal",
        description="Complete the draft proposal for the client meeting",
        due_date=now + timedelta(minutes=30),
        estimated_hours=1.5,
        priority="high"
    )
    
    # Create a task due in 1 hour
    task2 = Task(
        title="Review code changes",
        description="Review pull request #123 and provide feedback",
        due_date=now + timedelta(hours=1),
        estimated_hours=0.5,
        priority="medium"
    )
    
    # Add tasks to the reminder service
    reminder_service.add_task(task1)
    reminder_service.add_task(task2)
    
    # Start the reminder service with our callback
    reminder_service.start(reminder_callback=reminder_callback)
    
    try:
        logger.info("Reminder service is running. Press Ctrl+C to exit.")
        logger.info(f"Added tasks:")
        logger.info(f"  - {task1.title} (due in 30 minutes)")
        logger.info(f"  - {task2.title} (due in 1 hour)")
        
        # Keep the script running
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        # Stop the reminder service
        reminder_service.stop()

if __name__ == "__main__":
    main() 