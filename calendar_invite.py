import json
import os
import smtplib
import uuid
from datetime import datetime, timedelta
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional, Union, cast

from dotenv import load_dotenv
from icalendar import Calendar, Event, vCalAddress, vText

# Load environment variables
load_dotenv()


def create_calendar_invite(
    summary: str,
    start_time: str,
    end_time: str,
    description: str,
    location: str,
    attendees: List[str],
    organizer_email: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Creates an iCalendar invite.

    Args:
        summary: Meeting title
        start_time: ISO formatted start time (YYYY-MM-DDTHH:MM:SS)
        end_time: ISO formatted end time (YYYY-MM-DDTHH:MM:SS)
        description: Meeting description
        location: Meeting location or video conference link
        attendees: List of attendee email addresses
        organizer_email: Email of the meeting organizer (defaults to SENDER_EMAIL env var)

    Returns:
        Dictionary with calendar data and success status
    """
    try:
        # Create calendar instance
        cal = Calendar()
        cal.add("prodid", "-//Meeting Assistant//calendar_invite.py//EN")
        cal.add("version", "2.0")
        cal.add("method", "REQUEST")

        # Create event
        event = Event()
        event_uid = str(uuid.uuid4())
        event.add("uid", event_uid)
        event.add("summary", summary)
        event.add("description", description)
        event.add("location", location)

        # Parse start and end times
        try:
            start_dt = datetime.fromisoformat(start_time)
            end_dt = datetime.fromisoformat(end_time)
            event.add("dtstart", start_dt)
            event.add("dtend", end_dt)
        except ValueError as e:
            return {"success": False, "error": f"Invalid date format: {str(e)}"}

        # Add creation timestamp
        event.add("dtstamp", datetime.now())

        # Set up organizer
        organizer = organizer_email or os.environ["SENDER_EMAIL"]
        if not organizer:
            return {
                "success": False,
                "error": "Organizer email not specified and SENDER_EMAIL not set",
            }

        organizer_addr = vCalAddress(f"MAILTO:{organizer}")
        organizer_addr.params["cn"] = vText(organizer.split("@")[0])
        event["organizer"] = organizer_addr

        # Add attendees
        for attendee_email in attendees:
            attendee = vCalAddress(f"MAILTO:{attendee_email}")
            attendee.params["cn"] = vText(attendee_email.split("@")[0])
            attendee.params["ROLE"] = vText("REQ-PARTICIPANT")
            attendee.params["PARTSTAT"] = vText("NEEDS-ACTION")
            attendee.params["RSVP"] = vText("TRUE")
            event.add("attendee", attendee, encode=True)

        # Add the event to the calendar
        cal.add_component(event)

        return {
            "success": True,
            "calendar": cal.to_ical().decode("utf-8"),
            "event_uid": event_uid,
            "summary": summary,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def send_calendar_invite(
    recipients: Union[str, List[str]], subject: str, body: str, calendar_data: str
) -> Dict[str, Any]:
    """
    Sends a calendar invite as an email attachment.

    Args:
        recipients: Email address(es) of recipients
        subject: Email subject
        body: Email body text
        calendar_data: iCalendar data as string

    Returns:
        Dictionary with success status and message
    """
    if isinstance(recipients, str):
        recipients = [recipients]

    # Validate environment variables
    sender_email = os.environ.get("SENDER_EMAIL")
    sender_password = os.environ.get("SENDER_PASSWORD")
    smtp_server = os.environ.get("SMTP_SERVER")
    smtp_port_str = os.environ.get("SMTP_PORT", "587")
    smtp_port = int(smtp_port_str) if smtp_port_str.isdigit() else 587

    if not all([sender_email, sender_password, smtp_server]):
        return {
            "success": False,
            "error": "Missing required environment variables (SENDER_EMAIL, SENDER_PASSWORD, SMTP_SERVER)",
        }

    # Cast None types to str to satisfy type checker
    sender_email_str = cast(str, sender_email)
    sender_password_str = cast(str, sender_password)
    smtp_server_str = cast(str, smtp_server)

    try:
        # Create message container
        message = MIMEMultipart("mixed")
        message["Subject"] = subject
        message["From"] = sender_email_str
        message["To"] = ", ".join(recipients)

        # Create message alternative for both plain text and HTML
        message_alt = MIMEMultipart("alternative")

        # Add text body
        text_part = MIMEText(body, "plain")
        message_alt.attach(text_part)

        # Add HTML version (optional)
        html_body = f"<html><body>{body.replace('\n', '<br>')}</body></html>"
        html_part = MIMEText(html_body, "html")
        message_alt.attach(html_part)

        # Attach alternative content
        message.attach(message_alt)

        # Attach the calendar invite
        cal_attachment = MIMEBase("text", "calendar", method="REQUEST")
        cal_attachment.set_payload(calendar_data)
        encoders.encode_base64(cal_attachment)
        cal_attachment.add_header(
            "Content-Disposition", "attachment", filename="invite.ics"
        )
        message.attach(cal_attachment)

        # Connect to server and send
        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_server_str, smtp_port) as server:
                server.login(sender_email_str, sender_password_str)
                server.sendmail(sender_email_str, recipients, message.as_string())
        else:
            with smtplib.SMTP(smtp_server_str, smtp_port) as server:
                server.starttls()
                server.login(sender_email_str, sender_password_str)
                server.sendmail(sender_email_str, recipients, message.as_string())

        return {
            "success": True,
            "message": f"Calendar invite sent to {', '.join(recipients)}",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def create_and_send_calendar_invite(
    summary: str,
    start_time: str,
    end_time: Optional[str] = None,
    duration_minutes: int = 60,
    description: str = "",
    location: str = "",
    attendees: Optional[List[str]] = None,
    organizer_email: Optional[str] = None,
) -> str:
    """
    Creates and sends a calendar invitation to specified attendees.

    Args:
        summary: Meeting title
        start_time: ISO formatted start time (YYYY-MM-DDTHH:MM:SS)
        end_time: ISO formatted end time (optional if duration_minutes provided)
        duration_minutes: Duration in minutes (used if end_time not provided)
        description: Meeting description
        location: Meeting location or video conference link
        attendees: List of attendee email addresses
        organizer_email: Email of the meeting organizer

    Returns:
        JSON string with result information
    """
    if attendees is None:
        attendees = []

    # Calculate end time if not provided
    calculated_end_time = end_time
    if not calculated_end_time and duration_minutes:
        try:
            start_dt = datetime.fromisoformat(start_time)
            end_dt = start_dt + timedelta(minutes=duration_minutes)
            calculated_end_time = end_dt.isoformat()
        except ValueError:
            return json.dumps(
                {
                    "success": False,
                    "error": f"Invalid start_time format: {start_time}. Use ISO format (YYYY-MM-DDTHH:MM:SS).",
                }
            )

    # Ensure end_time is not None at this point
    if calculated_end_time is None:
        return json.dumps(
            {
                "success": False,
                "error": "Either end_time or duration_minutes must be provided",
            }
        )

    # Create the calendar invite
    cal_result = create_calendar_invite(
        summary=summary,
        start_time=start_time,
        end_time=calculated_end_time,
        description=description,
        location=location,
        attendees=attendees,
        organizer_email=organizer_email,
    )

    if not cal_result["success"]:
        return json.dumps(cal_result)

    # Send the invite
    email_subject = f"Meeting Invitation: {summary}"
    email_body = f"""
You're invited to: {summary}

When: {start_time} to {calculated_end_time}
Where: {location}

{description}

This is a calendar invitation from the Meeting Assistant.
"""

    email_result = send_calendar_invite(
        recipients=attendees,
        subject=email_subject,
        body=email_body,
        calendar_data=cal_result["calendar"],
    )

    result = {
        "success": email_result["success"],
        "calendar_created": True,
        "email_sent": email_result["success"],
        "summary": summary,
        "start_time": start_time,
        "end_time": calculated_end_time,
        "attendees": attendees,
    }

    if not email_result["success"]:
        result["error"] = email_result.get(
            "error", "Unknown error sending calendar invite"
        )

    return json.dumps(result)


if __name__ == "__main__":
    # Example usage
    result = create_and_send_calendar_invite(
        summary="Team Status Meeting",
        start_time="2023-12-01T14:00:00",
        duration_minutes=45,
        description="Weekly team status update meeting.\nPlease prepare your project updates.",
        location="Conference Room A or https://meet.google.com/abc-defg-hij",
        attendees=["jgoldstein46@gmail.com"],
    )

    print(result)
