import json
from datetime import datetime, timedelta

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

    def _calculate_end_time(self, start_time, duration_minutes):
        """Helper to calculate end time from start time and duration"""
        try:
            start = datetime.fromisoformat(start_time)
            end = start + timedelta(minutes=duration_minutes)
            return end.isoformat()
        except ValueError:
            # Handle non-ISO format times
            return f"start_time + {duration_minutes} minutes"
