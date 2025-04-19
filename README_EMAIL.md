# Setting Up Email Reminders with Amazon SES

This application uses Amazon Simple Email Service (SES) to send task reminders. Follow these steps to set up email reminders:

## Prerequisites

1. An AWS account with access to Amazon SES
2. Python 3.6+ with the boto3 library installed
3. AWS credentials configured

## Setup Steps

### 1. Install Required Dependencies

```bash
pip install boto3
```

### 2. Verify Your Email Address in SES

Before sending emails with Amazon SES, you need to verify your sender and recipient email addresses (if your account is still in the sandbox).

1. Go to the [Amazon SES Console](https://console.aws.amazon.com/ses/)
2. Navigate to "Identity Management" > "Email Addresses"
3. Click "Verify a New Email Address"
4. Enter your email address and click "Verify This Email Address"
5. Check your email inbox and click the verification link

### 3. Configure AWS Credentials

Set up your AWS credentials using one of these methods:

#### Option A: Environment Variables

```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-east-1  # or your preferred region
export EMAIL_SENDER=your-verified@email.com
```

#### Option B: AWS Credentials File

Create or update the file `~/.aws/credentials`:

```
[default]
aws_access_key_id = your_access_key
aws_secret_access_key = your_secret_key
```

Create or update the file `~/.aws/config`:

```
[default]
region = us-east-1
```

#### Option C: IAM Role (for EC2 instances or Lambda functions)

If you're running the application on AWS, configure an IAM role with appropriate SES permissions.

### 4. Run the Application

Start the application:

```bash
streamlit run streamlit_app.py
```

## Testing Email Functionality

To test if your email setup is working correctly:

1. Create a task with a due date close to the current time
2. Set a reminder buffer that will trigger an email soon
3. Check the console logs for confirmation that the email was sent
4. Check your inbox for the reminder email

## Troubleshooting

### Common Issues:

1. **Email not sending**: 
   - Check if you've verified your email addresses in SES
   - Verify AWS credentials are correctly set up
   - Look at application logs for specific error messages

2. **ClientError - Email address is not verified**:
   - Verify both sender and recipient emails in the SES console
   - Remember that if your account is in the sandbox, you must verify all sender and recipient addresses

3. **Sending rate exceeded**:
   - If you're sending many emails, you might hit SES limits
   - Request a sending limit increase in the AWS Console

## Moving to Production

When you're ready to send emails to non-verified recipients:

1. Move your SES account out of the sandbox by [requesting production access](https://docs.aws.amazon.com/ses/latest/dg/request-production-access.html)
2. Consider setting up domain verification instead of individual email addresses
3. Implement bounce and complaint handling

## Resources

- [Amazon SES Documentation](https://docs.aws.amazon.com/ses/latest/dg/Welcome.html)
- [Boto3 SES Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ses.html)
- [AWS SDK for Python](https://aws.amazon.com/sdk-for-python/) 