# Email Scheduling and Throttling with Elastic Email

This project demonstrates how to send emails with scheduling and throttling capabilities using the **Elastic Email API**. The system is designed to handle email campaigns with custom intervals and throttled sends, preventing overloading the email service.

## Table of Contents

- [Setup and Configuration](#setup-and-configuration)
- [Steps to Configure Email Scheduling and Throttling](#steps-to-configure-email-scheduling-and-throttling)
- [Usage Instructions](#usage-instructions)
- [Optional: Video Demonstration](#optional-video-demonstration)
- [Additional Resources](#additional-resources)

---

## Setup and Configuration

### 1. **Obtain API Key from Elastic Email**

To use Elastic Email for sending emails programmatically, you need an API key. Follow these steps to obtain it:

1. Visit the [Elastic Email website](https://app.elasticemail.com/).
2. Sign in to your account or create a new account.
3. Once logged in, navigate to **Account** > **API Keys** in the Elastic Email dashboard.
4. Click **Add API Key**, name your key, and select the permissions (read, write, etc.).
5. Copy the generated API key. You’ll need it to configure the email sending script.

### 2. **Configure API Key in Your Project**

You need to securely store and use your API key. Follow these steps:

1. Create a `.env` file in your project’s root directory (if it doesn't already exist).
2. Add your Elastic Email API key to the `.env` file as follows:

    ```
    ELASTIC_EMAIL_API_KEY=your_api_key_here
    ```

3. Ensure that your Python script can access this key using the `os.getenv()` method.

---

## Steps to Configure Email Scheduling and Throttling

### Email Scheduling

Elastic Email does not provide a direct API for scheduling emails. However, you can achieve email scheduling by using a Python scheduling library such as **APScheduler**.

#### Install APScheduler:

```bash
pip install apscheduler
```

#### Example Code for Email Scheduling:

```python
from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import datetime

scheduler = BlockingScheduler()

def send_scheduled_email():
    subject = "Scheduled Email"
    body = "This is a scheduled email."
    to_email = "recipient@example.com"
    send_email(subject, body, to_email)
    print(f"Email sent at {datetime.now()}")

# Schedule the email to send every 24 hours, starting at a specific date and time
scheduler.add_job(send_scheduled_email, 'interval', hours=24, start_date='2024-11-10 10:30:00')
scheduler.start()
```

### Email Throttling

To control the rate of email sends (throttling), use **time.sleep()** to insert delays between email sends. This prevents exceeding the rate limits of your ESP.

#### Example Code for Email Throttling:

```python
import time

def send_email_with_throttling(subject, body, to_email, throttle_interval=60):
    # Send email
    send_email(subject, body, to_email)
    print(f"Email sent to {to_email}")
    
    # Throttle the sending of emails by waiting for a specified interval
    time.sleep(throttle_interval)  # Delay between emails (in seconds)

# Example usage:
send_email_with_throttling('Test Subject', 'Test Body', 'recipient1@example.com', throttle_interval=60)
send_email_with_throttling('Test Subject', 'Test Body', 'recipient2@example.com', throttle_interval=60)
```

In this example, there’s a 60-second interval between email sends.

---

## Usage Instructions

### 1. **Configure the `.env` File**
   - Ensure you have the `.env` file with your Elastic Email API key:

    ```
    ELASTIC_EMAIL_API_KEY=your_api_key_here
    ```

### 2. **Email Scheduling**
   - Use **APScheduler** or **schedule** to configure when to send emails, including one-time or recurring intervals.

### 3. **Email Throttling**
   - Implement throttling using `time.sleep()` or another mechanism to avoid exceeding Elastic Email's rate limits.

### 4. **Running the Script**
   - Execute the Python script that integrates Elastic Email API. This will trigger the email sending at scheduled times with throttling applied.

#### Example to Send Emails with Scheduling and Throttling:

```python
def send_scheduled_email():
    subject = "Scheduled Email"
    body = "This is an email sent after a delay."
    to_email = "recipient@example.com"
    send_email(subject, body, to_email)

# Example usage with throttling and scheduling
send_email_with_throttling('Scheduled Subject', 'Scheduled Body', 'recipient@example.com', throttle_interval=120)
```

### 5. **Monitor Sending Results**
   - You can check the **Elastic Email Dashboard** for detailed reports about sent emails.

---

## Optional: Video Demonstration

A short demonstration video is available to showcase how to set up and use the email scheduling and throttling system with Elastic Email. This video will walk you through obtaining the API key, configuring the `.env` file, and running the email scheduler and throttle.

[Watch the video demonstration here](#) *(Replace with actual video link if available)*.

---

## Additional Resources

- [Elastic Email API Documentation](https://elasticemail.com/developers/)
- [APScheduler Documentation](https://apscheduler.readthedocs.io/en/stable/)
- [Python `requests` Library](https://requests.readthedocs.io/en/latest/)

---

By following the above steps, you should be able to integrate email scheduling and throttling into your project using the Elastic Email API.

---

