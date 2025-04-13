import smtplib
from email.mime.text import MIMEText
import os # Import os to potentially use environment variables later
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def send_email(recipient: str, subject: str, body: str):
    """
    Sends an email using smtplib to the specified recipient.
    
    Requires configuration of sender email, password/token, and SMTP server details
    via environment variables.
    """
    
    # Example using smtplib (requires configuration)
    try:
        # Credentials loaded from environment variables (set via .env or system)
        sender_email = os.environ.get("SENDER_EMAIL") 
        sender_password = os.environ.get("SENDER_PASSWORD")
        smtp_server = os.environ.get("SMTP_SERVER")
        # Removed recipient_email loading from .env
        smtp_port = int(os.environ.get("SMTP_PORT", 587)) # Keep default if not set

        # Check if all required SENDER variables are loaded
        if not all([sender_email, sender_password, smtp_server]):
            print("Error: Missing required sender environment variables (SENDER_EMAIL, SENDER_PASSWORD, SMTP_SERVER).")
            print("Please ensure they are set in your .env file or system environment.")
            return {"success": False, "error": "Missing sender configuration"}

        print(f"Attempting to send email to {recipient} with subject: {subject}")

        message = MIMEText(body)
        message['Subject'] = subject
        message['From'] = sender_email
        message['To'] = recipient # Use passed recipient argument

        # Connect to server, login, and send email
        # Use SMTP_SSL for port 465
        if smtp_port == 465:
             with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, recipient, message.as_string())
        else: # Assume port 587 or other requires starttls
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls() # Secure the connection
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, recipient, message.as_string())
                
        print("--- Email Sent (Actual) ---")
        return {"success": True, "message": "Email sent successfully."}
    except Exception as e:
        print(f"Error sending email: {e}")
        # Log the error properly in a real application
        return {"success": False, "error": str(e)}

if __name__ == '__main__':
    # Example usage for testing
    # Provide a recipient for testing
    send_email(
        recipient=os.environ.get("RECIPIENT_EMAIL"),
        subject="4/14 10AM Meeting Reminder",
        body="""
        Just a friendly reminder about your meeting on Monday, April 14th at 10 AM with Lidia H. Agenda:
        - Review project status
        - Discuss upcoming tasks
        - Review hiring updates
        - Operational risks
        Please prepare any materials you'd like to share.
        """
    )
