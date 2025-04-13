import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from calendar_invite import create_and_send_calendar_invite
from get_employee_email import get_email_from_assignee
from jira_ticket import create_jira_ticket
from knowledge_search import search_knowledge


class ToolManager:
    """Manages tool implementations for the agent"""

    def __init__(self, config=None):
        self.config = config or {}

    def execute_tool(self, tool_name, tool_args):
        """Route tool calls to the appropriate implementation"""
        if tool_name == "search_knowledge":
            return self.search_knowledge(tool_args["query"])
        elif tool_name == "create_jira_ticket":
            return self.create_jira_ticket(
                summary=tool_args["summary"],
                description=tool_args["description"],
                issue_type=tool_args.get("issue_type", "Task"),
                labels=tool_args.get("labels", []),
                assignee=tool_args.get("assignee"),
            )
        elif tool_name == "create_calendar_invite":
            return self.create_calendar_invite(
                summary=tool_args["summary"],
                start_time=tool_args["start_time"],
                end_time=tool_args.get("end_time"),
                duration_minutes=tool_args.get("duration_minutes", 60),
                description=tool_args.get("description", ""),
                location=tool_args.get("location", ""),
                attendees=tool_args.get("attendees", []),
                organizer_email=tool_args.get("organizer_email"),
            )
        else:
            return {"error": f"Unknown tool: {tool_name}"}

    def search_knowledge(self, query: str):
        """
        Execute the search_knowledge tool and handle the JSON string response format.

        Args:
            query: The search query

        Returns:
            dict: A dictionary suitable for passing to the agent API
        """
        # Get the JSON string response from the search function
        json_response = search_knowledge(query)

        # The response is already a JSON string, so we can return it directly
        # The agent_flow._process_claude_response method will handle it appropriately
        return json_response

    def create_jira_ticket(
        self,
        summary: str,
        description: str,
        issue_type: str = "Task",
        labels: list = [],
        assignee: str | None = None,
    ):
        """
        Create a Jira ticket and return the response.

        Args:
            project_key: The Jira project key (e.g., "SCRUM")
            summary: The summary/title of the ticket
            description: The detailed description of the ticket
            issue_type: The type of issue (default: "Task")
            labels: List of labels to add to the ticket
            assignee: Account ID or email of the user to assign the ticket to (default: None)

        Returns:
            str: JSON string response suitable for the agent API
        """
        try:
            result = create_jira_ticket(
                summary=summary,
                description=description,
                issue_type=issue_type,
                labels=labels,
                assignee=assignee,
            )
            # Convert the result to a JSON string
            return json.dumps(result)
        except Exception as e:
            error_result = {
                "success": False,
                "message": f"Error creating Jira ticket: {str(e)}",
            }
            return json.dumps(error_result)

    def create_calendar_invite(
        self,
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
        Create and send a calendar invitation.

        Args:
            summary: Meeting title
            start_time: ISO formatted start time (YYYY-MM-DDTHH:MM:SS)
            end_time: ISO formatted end time (optional if duration_minutes provided)
            duration_minutes: Duration in minutes (used if end_time not provided)
            description: Meeting description
            location: Meeting location or video conference link
            attendees: List of attendee names as they appear in Jira
            organizer_email: Email of the meeting organizer

        Returns:
            str: JSON string with result information
        """
        try:
            # Convert team member names to email addresses
            attendee_emails = []

            # Process team members if provided
            if attendees:
                for attendee in attendees:
                    email = get_email_from_assignee(attendee)
                    if email:
                        attendee_emails.append(email)
                    else:
                        print(
                            f"Warning: Could not find email for team member: {attendee}"
                        )

            # If no valid attendees, return error
            if not attendee_emails:
                return json.dumps(
                    {
                        "success": False,
                        "error": "No valid attendee emails could be determined from the provided team members or additional emails",
                    }
                )

            # Call the calendar invite function with resolved emails
            return create_and_send_calendar_invite(
                summary=summary,
                start_time=start_time,
                end_time=end_time,
                duration_minutes=duration_minutes,
                description=description,
                location=location,
                attendees=attendee_emails,
                organizer_email=organizer_email,
            )
        except Exception as e:
            error_result = {
                "success": False,
                "error": f"Error creating calendar invite: {str(e)}",
            }
            return json.dumps(error_result)

    def _calculate_end_time(self, start_time, duration_minutes):
        """Helper to calculate end time from start time and duration"""
        try:
            start = datetime.fromisoformat(start_time)
            end = start + timedelta(minutes=duration_minutes)
            return end.isoformat()
        except ValueError:
            # Handle non-ISO format times
            return f"start_time + {duration_minutes} minutes"
