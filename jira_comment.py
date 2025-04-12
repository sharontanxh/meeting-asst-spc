import os

import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

load_dotenv()

JIRA_DOMAIN: str = os.environ["JIRA_DOMAIN"]
JIRA_EMAIL: str = os.environ["JIRA_EMAIL"]
JIRA_API_TOKEN: str = os.environ["JIRA_API_TOKEN"]


def add_jira_comment(ticket_key: str, comment: str) -> dict:
    """
    Add a comment to a Jira ticket.

    Args:
        ticket_key: The Jira ticket key (e.g., "SPC-001")
        comment: The comment text to add

    Returns:
        dict: Response from Jira API
    """
    if not all([JIRA_DOMAIN, JIRA_EMAIL, JIRA_API_TOKEN]):
        raise ValueError("Missing required Jira environment variables")

    url = f"https://{JIRA_DOMAIN}/rest/api/3/issue/{ticket_key}/comment"

    payload = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": comment}]}
            ],
        }
    }

    auth = HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)
    headers = {"Accept": "application/json", "Content-Type": "application/json"}

    response = requests.post(url, json=payload, headers=headers, auth=auth)
    print("Got response", response.json())
    # response.raise_for_status()

    return response.json()


if __name__ == "__main__":
    print(add_jira_comment("SCRUM-8", "This is a test comment"))
