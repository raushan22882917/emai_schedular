import requests
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import io
import csv
import gspread
from datetime import datetime, timedelta
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask, request, jsonify, render_template, redirect, url_for
import time
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
import os
import logging

# Load environment variables from .env file
load_dotenv()


# Initialize Flask app
app = Flask(__name__)

# Initialize APScheduler
scheduler = BackgroundScheduler()
scheduler.start()

# Database connection setup (singleton pattern)
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

API_KEY = os.getenv("API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM")
ELASTIC_EMAIL_URL = os.getenv("ELASTIC_EMAIL_URL")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_API_URL = os.getenv("LLM_API_URL")

def send_email(api_key, sender_email, recipient_email, subject, body, company_name, location, products):
    try:
        params = {
            "apikey": api_key,
            "from": sender_email,
            "to": recipient_email,
            "subject": subject,
            "bodyText": body,
        }

        # Send the email request
        response = requests.post(ELASTIC_EMAIL_URL, data=params)
        
        if response.status_code == 200:
            print(f"Email sent to {recipient_email}")
            # Log successful email in the database
            sent_time = datetime.now()
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO emails_data (recipient_email, subject, body, status, sent_time, company_name, location, products)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (recipient_email, subject, body, 'sent', sent_time, company_name, location, products)
                    )
                    conn.commit()
        else:
            print(f"Failed to send email. Status code: {response.status_code}")
            log_failed_email(recipient_email, subject, body, company_name, location, products)

    except Exception as e:
        print(f"Exception occurred: {str(e)}")
        log_failed_email(recipient_email, subject, body, company_name, location, products)
logging.basicConfig(filename='app.log', level=logging.ERROR, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
# Function to log failed email attempt
def log_failed_email(recipient_email, subject, body, company_name, location, products):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO emails_data (recipient_email, subject, body, status, company_name, location, products)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (recipient_email, subject, body, 'failed', company_name, location, products)
                )
            conn.commit()  # Commit outside the cursor's context manager for better error handling
    except psycopg2.DatabaseError as e:
        # Rollback if there is any error during the transaction
        if conn:
            conn.rollback()
        logging.error(f"Failed to log failed email for {recipient_email}: {e}")
    except Exception as e:
        # Catch-all for any other exceptions
        logging.error(f"An unexpected error occurred: {e}")

# Function to check the email sending rate (max 50 per hour)
# Check the email count in the past hour
def check_email_limit():
    try:
        one_hour_ago = datetime.now() - timedelta(hours=1)
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM emails_data 
                    WHERE sent_time > %s AND status = 'sent'
                    """, (one_hour_ago,)
                )
                count = cursor.fetchone()[0]
                return count
    except Exception as e:
        logging.error(f"Error checking email limit: {e}")
        return None

# Send email with rate limit and retry mechanism
def send_email_with_limit(prompt, data, batch_size, interval_minutes, max_retry_attempts=3):
    email_limit = check_email_limit()
    
    if email_limit is None:
        logging.warning("Could not determine email limit. Aborting email send.")
        return

    if email_limit < 50:
        subject = "Scheduled Email"
        
        for recipient in data:
            recipient_email = recipient.get('Email')
            company_name = recipient.get('Company Name')
            location = recipient.get('Location')
            products = recipient.get('Products')
            
            if recipient_email:
                personalized_prompt = fill_placeholders(prompt, recipient)
                
                # Retry sending email with backoff if there are transient issues
                success = False
                backoff_time = 1  # start with 1 second
                
                for attempt in range(max_retry_attempts):
                    try:
                        send_email(API_KEY, EMAIL_FROM, recipient_email, subject, personalized_prompt, company_name, location, products)
                        success = True
                        break
                    except ESPRateLimitError as e:
                        logging.warning(f"Rate limit hit. Retrying in {backoff_time} seconds...")
                        time.sleep(backoff_time)
                        backoff_time *= 2  # exponential backoff
                    except Exception as e:
                        logging.error(f"Failed to send email to {recipient_email}: {e}")
                        break

                if not success:
                    log_failed_email(recipient_email, subject, personalized_prompt, company_name, location, products)
            else:
                logging.warning("No email found for recipient.")
                
            # Respect interval between emails
            time.sleep(interval_minutes * 60)
    else:
        logging.info("Email limit reached. Try again later or schedule for next hour.")

# Function for scheduled and batched email sending
def send_scheduled_emails(prompt, data, batch_size, interval_minutes):
    send_email_with_limit(prompt, data, batch_size, interval_minutes)

def schedule_emails(prompt, data, schedule_type, interval=None, specific_time=None, batch_size=50, interval_minutes=1):
    if schedule_type == 'specific_time':
        scheduled_time = datetime.strptime(specific_time, "%Y-%m-%dT%H:%M")
        scheduler.add_job(
            send_scheduled_emails, 'date', run_date=scheduled_time,
            args=[prompt, data, batch_size, interval_minutes]
        )
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                for recipient in data:
                    cursor.execute(
                        """
                        INSERT INTO emails_data (recipient_email, subject, body, status, scheduled_time, company_name, location, products)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (recipient.get('Email'), "Scheduled Email", prompt, 'scheduled', scheduled_time, recipient.get('Company Name'), recipient.get('Location'), recipient.get('Products'))
                    )
                    conn.commit()
    elif schedule_type == 'interval':
        scheduler.add_job(
            send_scheduled_emails, 'interval', minutes=interval_minutes,
            args=[prompt, data, batch_size, interval_minutes]
        )

def fill_placeholders(prompt, data_row):
    filled_prompt = prompt
    for key, value in data_row.items():
        placeholder = f"{{{key}}}"  # e.g., "{Company Name}"
        filled_prompt = filled_prompt.replace(placeholder, str(value))
    return filled_prompt
# Function to generate email content using Groq API (LLM)
def generate_email_content(prompt, data_row):
    headers = {'Authorization': f'Bearer {LLM_API_KEY}'}
    personalized_prompt = fill_placeholders(prompt, data_row)
    response = requests.post(LLM_API_URL, headers=headers, data={"prompt": personalized_prompt})
    
    if response.status_code == 200:
        result = response.json()
        return result.get("generated_text", "")
    else:
        print("Failed to generate content via Groq API.")
        return None
@app.route('/analytics', methods=['GET'])
def analytics():
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT status, COUNT(*) FROM emails_data GROUP BY status")
            results = cursor.fetchall()
            analytics_data = {
                'sent_count': 0,
                'pending_count': 0,
                'scheduled_count': 0,
                'failed_count': 0
            }
            for status, count in results:
                if status == 'sent':
                    analytics_data['sent_count'] = count
                elif status == 'pending':
                    analytics_data['pending_count'] = count
                elif status == 'scheduled':
                    analytics_data['scheduled_count'] = count
                elif status == 'failed':
                    analytics_data['failed_count'] = count
    return jsonify(analytics_data)
# Home page (index) route
@app.route('/')
def index():
    return render_template("index.html")

# Customize email and schedule it
@app.route('/customize_email', methods=['POST'])
def customize_email():
    prompt = request.form.get('prompt')
    data_file = request.files.get('data_file')
    google_sheet_link = request.form.get('google_sheet_link')
    schedule_type = request.form.get('schedule_type')
    interval = int(request.form.get('interval', 1))
    specific_time = request.form.get('specific_time')

    data = []
    if data_file:
        stream = io.StringIO(data_file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.DictReader(stream)
        data = list(csv_reader)
    elif google_sheet_link:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/spreadsheets',
                 'https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name('service-account.json', scope)
        client = gspread.authorize(creds)
        sheet_id = google_sheet_link.split("/")[5]
        sheet = client.open_by_key(sheet_id).sheet1
        data = sheet.get_all_records()

    if data:
        schedule_emails(prompt, data, schedule_type, interval, specific_time)

    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    emails = []
    email_counts = []
    daily_email_counts = []

    now = datetime.now()
    current_hour = now.replace(minute=0, second=0, microsecond=0)
    hours = [(current_hour - timedelta(hours=i)).strftime('%Y-%m-%d %H:%M:%S') for i in range(24)]

    API_KEY = "AFDAD532B629635AABD9B940250EB1DDA007AF5CBA73EF958B0FC792DEA21F2F8F033AE18DE86E814F67B21C90C3BBA7"
    ELASTIC_EMAIL_URL = "https://api.elasticemail.com/v4/statistics"

    from_date = "2024-01-01T00:00:00"
    to_date = now.strftime("%Y-%m-%dT%H:%M:%S")
    params = {
        "apikey": API_KEY,
        "from": from_date,
        "to": to_date
    }
    elastic_email_stats = {}
    
    try:
        response = requests.get(ELASTIC_EMAIL_URL, params=params)
        if response.status_code == 200:
            stats = response.json()
            elastic_email_stats = {
                "recipients": stats['Recipients'],
                "email_total": stats['EmailTotal'],
                "sms_total": stats['SmsTotal'],
                "delivered": stats['Delivered'],
                "bounced": stats['Bounced'],
                "in_progress": stats['InProgress'],
                "opened": stats['Opened'],
                "clicked": stats['Clicked'],
                "unsubscribed": stats['Unsubscribed'],
                "complaints": stats['Complaints'],
                "inbound": stats['Inbound'],
                "manual_cancel": stats['ManualCancel'],
                "not_delivered": stats['NotDelivered'],
            }
        else:
            print(f"Failed to retrieve statistics: {response.status_code}")
    except Exception as e:
        print(f"Error fetching Elastic Email statistics: {e}")

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT recipient_email, subject, body, status, scheduled_time, company_name, location, products
                    FROM emails_data
                """)
                results = cursor.fetchall()
                for row in results:
                    email_data = {
                        "recipient_email": row[0],
                        "status": row[3],
                        "scheduled_time": row[4],
                        "sent_time": row[4],
                        "company_name": row[5],
                    }
                    if row[3] == 'Sent':
                        email_data['delivery_status'] = 'Delivered'
                        email_data['opened'] = 'Yes'
                    elif row[3] == 'Scheduled':
                        email_data['delivery_status'] = 'N/A'
                        email_data['opened'] = 'N/A'
                    elif row[3] == 'Failed':
                        email_data['delivery_status'] = 'Bounced'
                        email_data['opened'] = 'No'
                    else:
                        email_data['delivery_status'] = 'N/A'
                        email_data['opened'] = 'N/A'
                    emails.append(email_data)

                for hour in hours:
                    next_hour = (datetime.strptime(hour, '%Y-%m-%d %H:%M:%S') + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
                    cursor.execute("""
                        SELECT COUNT(*) 
                        FROM emails_data 
                        WHERE sent_time >= %s AND sent_time < %s AND status = 'sent'
                    """, (hour, next_hour))
                    email_count = cursor.fetchone()[0]
                    email_counts.append((hour, email_count, next_hour))

                cursor.execute("""
                    SELECT 
                        DATE(scheduled_time) AS date,
                        COUNT(*) FILTER (WHERE status = 'scheduled') AS scheduled_count,
                        COUNT(*) FILTER (WHERE status = 'sent') AS sent_count
                    FROM emails_data
                    WHERE scheduled_time >= %s
                    GROUP BY DATE(scheduled_time)
                    ORDER BY DATE(scheduled_time) DESC
                """, (now - timedelta(days=7),))
                daily_results = cursor.fetchall()
                for row in daily_results:
                    daily_email_counts.append({
                        "date": row[0],
                        "scheduled_count": row[1],
                        "sent_count": row[2]
                    })

    except Exception as e:
        print(f"Error occurred: {e}")
        return render_template('error.html', error_message=str(e))

    return render_template(
        'dashboard.html',
        emails=emails,
        email_counts=email_counts,
        daily_email_counts=daily_email_counts,
        elastic_email_stats=elastic_email_stats
    )

if __name__ == "__main__":
    app.run(debug=True)
