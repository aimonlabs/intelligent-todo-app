import logging
import random
import os
import boto3
from botocore.exceptions import ClientError
from typing import List, Optional, Dict, Any

class EmailService:
    """Service for sending email notifications and reminders using Amazon SES"""
    
    def __init__(
        self,
        aws_region: str = None,
        sender_email: Optional[str] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the email service with Amazon SES
        
        Args:
            aws_region: AWS Region for SES (defaults to env var AWS_REGION or 'us-east-1')
            sender_email: Email to send from (defaults to env var EMAIL_SENDER)
            logger: Logger instance for tracking operations
        """
        self.sender_email = sender_email or os.environ.get("EMAIL_SENDER")
        self.aws_region = aws_region or os.environ.get("AWS_REGION", "us-east-1")
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize SES client
        try:
            self.ses_client = boto3.client('ses', region_name=self.aws_region)
            self.logger.info(f"Initialized Amazon SES client in region {self.aws_region}")
        except Exception as e:
            self.logger.error(f"Failed to initialize Amazon SES client: {str(e)}")
            self.ses_client = None
        
        # Fun reminder messages for task reminders
        self.reminder_templates = [
            "⏰ Don't forget about your task '{task_name}'!",
            "👋 Just a friendly reminder about '{task_name}'",
            "⚡ Time to focus on '{task_name}'",
            "🚀 Ready to tackle '{task_name}'?",
            "📝 Your to-do list is calling: '{task_name}'",
            "🌟 You've got this! Time to work on '{task_name}'",
            "🔔 Reminder: '{task_name}' needs your attention"
        ]
        
        if not self.sender_email:
            self.logger.warning(
                "Sender email not provided. Set EMAIL_SENDER environment variable "
                "or pass it to the constructor."
            )
    
    def send_email(
        self, 
        recipient_email: str, 
        subject: str, 
        body: str, 
        is_html: bool = False
    ) -> bool:
        """
        Send an email using Amazon SES
        
        Args:
            recipient_email: Email address to send to
            subject: Email subject line
            body: Email body content
            is_html: Whether the body content is HTML
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        if not self.sender_email:
            self.logger.error("Cannot send email: Missing sender email")
            return False
            
        if not self.ses_client:
            self.logger.error("Cannot send email: SES client not initialized")
            return False
            
        try:
            # Set up the email
            message = {
                'Subject': {
                    'Data': subject,
                    'Charset': 'UTF-8'
                },
                'Body': {}
            }
            
            # Add either HTML or plain text body
            if is_html:
                message['Body']['Html'] = {
                    'Data': body,
                    'Charset': 'UTF-8'
                }
                # Also include a text version for clients that don't support HTML
                # Simple stripping of HTML tags as a fallback
                text_body = body.replace('<', ' <').replace('>', '> ')
                message['Body']['Text'] = {
                    'Data': text_body,
                    'Charset': 'UTF-8'
                }
            else:
                message['Body']['Text'] = {
                    'Data': body,
                    'Charset': 'UTF-8'
                }
            
            # Send the email
            response = self.ses_client.send_email(
                Source=self.sender_email,
                Destination={
                    'ToAddresses': [recipient_email]
                },
                Message=message
            )
            
            self.logger.info(f"Email sent to {recipient_email}: {subject} (Message ID: {response['MessageId']})")
            return True
            
        except ClientError as e:
            self.logger.error(f"Failed to send email: {e.response['Error']['Message']}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error sending email: {str(e)}")
            return False
    
    def send_reminder(
        self,
        to_email: str,
        subject: str,
        task_description: str,
        due_date_str: str,
        estimated_hours: float,
        fun_message: Optional[str] = None
    ) -> bool:
        """
        Send a reminder email for a task using Amazon SES
        
        Args:
            to_email: Email address to send to
            subject: Email subject
            task_description: Description of the task
            due_date_str: Formatted due date string
            estimated_hours: Estimated hours to complete task
            fun_message: Optional custom fun message
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        # Generate a fun message if none provided
        if not fun_message:
            template = random.choice(self.reminder_templates)
            fun_message = template.format(task_name=task_description[:30])
            
        # Create HTML email content
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
            <h2 style="color: #333;">{subject}</h2>
            
            <div style="margin: 20px 0; padding: 15px; background-color: #f9f9f9; border-radius: 4px;">
                <p style="font-size: 16px; color: #555;">
                    <strong>Task:</strong> {task_description}
                </p>
                <p style="font-size: 16px; color: #555;">
                    <strong>Due:</strong> {due_date_str}
                </p>
                <p style="font-size: 16px; color: #555;">
                    <strong>Estimated time:</strong> {estimated_hours:.1f} hours
                </p>
            </div>
            
            <div style="margin-top: 20px; padding: 15px; background-color: #ffefd5; border-radius: 4px; text-align: center;">
                <p style="font-size: 18px; color: #ff7f50; font-weight: bold;">
                    {fun_message}
                </p>
            </div>
            
            <div style="margin-top: 30px; font-size: 14px; color: #999; text-align: center; padding-top: 15px; border-top: 1px solid #eee;">
                This is an automated reminder from your Todo App.
            </div>
        </div>
        """
        
        # Send the email
        return self.send_email(
            recipient_email=to_email,
            subject=subject,
            body=html_content,
            is_html=True
        )
            
    def send_batch_emails(
        self, 
        recipient_emails: List[str], 
        subject: str, 
        body: str, 
        is_html: bool = False
    ) -> int:
        """
        Send the same email to multiple recipients using Amazon SES
        
        Args:
            recipient_emails: List of email addresses
            subject: Email subject line
            body: Email body content
            is_html: Whether the body content is HTML
            
        Returns:
            int: Number of emails successfully sent
        """
        successful = 0
        for email in recipient_emails:
            if self.send_email(email, subject, body, is_html):
                successful += 1
                
        return successful 