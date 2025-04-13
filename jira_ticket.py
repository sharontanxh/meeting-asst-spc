import os
from datetime import datetime

import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

load_dotenv()

JIRA_DOMAIN: str = os.environ["JIRA_DOMAIN"]
JIRA_EMAIL: str = os.environ["JIRA_EMAIL"]
JIRA_API_TOKEN: str = os.environ["JIRA_API_TOKEN"]
PROJECT_KEY: str = "SCRUM"


def create_jira_ticket(
    summary: str,
    description: str,
    issue_type: str = "Task",
    labels: list = [],
    project_key: str = PROJECT_KEY,
    assignee: str | None = None,
) -> dict:
    """
    Create a new Jira ticket.

    Args:
        project_key: The Jira project key (e.g., "SCRUM")
        summary: The summary/title of the ticket
        description: The detailed description of the ticket
        issue_type: The type of issue (default: "Task")
        labels: List of labels to add to the ticket
        assignee: Account ID or email of the user to assign the ticket to (default: None)

    Returns:
        dict: Response from Jira API
    """
    if not all([JIRA_DOMAIN, JIRA_EMAIL, JIRA_API_TOKEN]):
        raise ValueError("Missing required Jira environment variables")

    url = f"https://{JIRA_DOMAIN}/rest/api/3/issue"

    payload = {
        "fields": {
            "project": {"key": PROJECT_KEY},
            "summary": summary,
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description}],
                    }
                ],
            },
            "issuetype": {"name": issue_type},
        }
    }

    # Add labels if provided
    if labels:
        payload["fields"]["labels"] = labels

    # Add assignee if provided
    if assignee:
        # TODO: Get this part working
        payload["fields"]["assignee"] = {"name": assignee}

    auth = HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)
    headers = {"Accept": "application/json", "Content-Type": "application/json"}

    response = requests.post(url, json=payload, headers=headers, auth=auth)
    print("Create ticket response:", response.status_code)

    if response.status_code == 201:
        return {
            "success": True,
            "message": f"Ticket created successfully",
            "data": response.json(),
        }
    else:
        try:
            error_data = response.json()
            return {
                "success": False,
                "message": f"Failed to create ticket: {error_data.get('errorMessages', ['Unknown error'])[0]}",
                "status_code": response.status_code,
                "data": error_data,
            }
        except:
            return {
                "success": False,
                "message": f"Failed to create ticket: {response.status_code}",
                "status_code": response.status_code,
            }


if __name__ == "__main__":
    # Test create ticket
    print(
        create_jira_ticket(
            project_key="SCRUM",
            summary=f"Test ticket from API {datetime.now()}",
            description="This is a test ticket created by the API",
            labels=["test", "api"],
            assignee="jgoldstein46@gmail.com",
        )
    )
