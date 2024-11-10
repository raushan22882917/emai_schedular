# Email Scheduling and Throttling with Elastic Email

This project demonstrates how to send emails with scheduling and throttling capabilities using the **Elastic Email API**. The system is designed to send emails with custom intervals and throttling, helping to manage the sending rate and prevent overloading the email service.

## Table of Contents

- [Setup and Configuration](#setup-and-configuration)
- [Steps to Configure Email Scheduling and Throttling](#steps-to-configure-email-scheduling-and-throttling)
- [Email Customization and Sending](#email-customization-and-sending)
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

### 2. **Get Service Account JSON from Google Cloud Console**

To integrate with Google Cloud APIs, such as using Google Sheets for data storage or Google Drive for file access, you will need a **service account JSON file** from Google Cloud Console.

#### Steps to Obtain a Service Account JSON File:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Navigate to **IAM & Admin** > **Service Accounts**.
3. Click **Create Service Account** and fill out the required information.
4. Once the service account is created, go to the **Keys** section and click **Add Key** > **Create new key**.
5. Select **JSON** and download the file. This file contains your service account credentials.
6. Place this JSON file in your project’s root directory and name it `service-account.json` (or any other preferred name).

### 3. **Configure API Keys and Service Account in Your Project**

1. Create a `.env` file in your project’s root directory (if it doesn't already exist).
2. Add your Elastic Email API key and Google service account path to the `.env` file as follows:

    ```
    ELASTIC_EMAIL_API_KEY=your_elastic_email_api_key
    GROQ_API_KEY=your_groq_api_key
    GOOGLE_APPLICATION_CREDENTIALS=service-account.json
    ```

3. Ensure that your Python script can access these keys using the `os.getenv()` method.

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

## Email Customization and Sending

### Content Generation

For each row of data, the content of the email is customized based on the user’s prompt and the row data. This is done using an LLMs API, such as the **Groq API**, to generate a response that is tailored to each recipient.

#### Example: Customizing Email Content Using Groq API

You can integrate **Groq API** for generating personalized content based on the row data. Here's how you can structure it:

```python
import requests

def generate_email_content(user_prompt, row_data):
    api_key = "your_groq_api_key"
    endpoint = "https://api.groq.com/generate"

    payload = {
        "prompt": user_prompt,
        "row_data": row_data,
    }

    response = requests.post(endpoint, json=payload, headers={"Authorization": f"Bearer {api_key}"})
    
    if response.status_code == 200:
        return response.json()["generated_content"]
    else:
        print("Error generating content:", response.text)
        return None

# Example of using the function
row_data = {"name": "John Doe", "subscription": "Premium"}
user_prompt = "Generate a welcome email for this user with their subscription plan."
custom_content = generate_email_content(user_prompt, row_data)
```

### Email Sending

Once the email content is generated, the next step is to customize the content for each recipient and send the email using the **Elastic Email API**.

#### Example Code for Sending Emails:

```python
import requests

def send_email(subject, body, to_email):
    api_key = "your_elastic_email_api_key"
    endpoint = "https://api.elasticemail.com/v4/email/send"

    payload = {
        "from": "your_email@example.com",
        "to": to_email,
        "subject": subject,
        "body": body,
        "apikey": api_key
    }

    response = requests.post(endpoint, data=payload)

    if response.status_code == 200:
        print(f"Email sent to {to_email}")
    else:
        print(f"Error sending email: {response.text}")
```

---

## Usage Instructions

### 1. **Configure the `.env` File**
   - Ensure you have the `.env` file with your Elastic Email API key, Groq API key, and Google service account JSON path:

    ```
    ELASTIC_EMAIL_API_KEY=your_elastic_email_api_key
    GROQ_API_KEY=your_groq_api_key
    GOOGLE_APPLICATION_CREDENTIALS=service-account.json
    ```

### 2. **Email Scheduling**
   - Use **APScheduler** or **schedule** to configure when to send emails, including one-time or recurring intervals.

### 3. **Email Throttling**
   - Implement throttling using `time.sleep()` or another mechanism to avoid exceeding Elastic Email's rate limits.

### 4. **Generate Custom Content for Each Email**
   - Use the **Groq API** to generate custom content for each recipient based on row data and the user’s prompt.

### 5. **Running the Script**
   - Execute the Python script that integrates Elastic Email API and Groq API. This will trigger the email sending at scheduled times with throttling applied.

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

### 6. **Monitor Sending Results**
   - You can check the **Elastic Email Dashboard** for detailed reports about sent emails.

---

## Optional: Video Demonstration

A short demonstration video is available to showcase how to set up and use the email scheduling and throttling system with Elastic Email. This video will walk you through obtaining the API key, configuring the `.env` file, and running the email scheduler and throttle.

[Watch the video demonstration here](https://drive.google.com/file/d/1iFXHgbsCyyy-O7j4ni-kKe7Zje2uqnb4/view?usp=sharing).

---

## Render Webpage

You can access the web version of this project, where you can configure email scheduling and throttling, via the following link:

[Visit the Webpage](https://email-schedular-zpn7.onrender.com)

---

## Additional Resources

- [Elastic Email API Documentation](https://elasticemail.com/developers/)
- [APScheduler Documentation](https://apscheduler.readthedocs.io/en/stable/)
- [Python `requests` Library](https://requests.readthedocs.io/en/latest/)
- [Groq API Documentation](https://groq.com/docs)
- [Google Cloud Service Accounts](https://

cloud.google.com/iam/docs/service-accounts)

---
