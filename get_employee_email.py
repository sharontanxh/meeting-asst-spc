import json

# Placeholder mapping of JIRA display names to email addresses
ASSIGNEE_EMAIL_MAP = {
    "[TEAM_MEMBER_1]": "jgoldstein46+1@gmail.com",
    "[TEAM_MEMBER_2]": "jgoldstein46+2@gmail.com",
    "[TEAM_MEMBER_3]": "jgoldstein46+3@gmail.com",
    "[TEAM_MEMBER_4]": "jgoldstein46+4@gmail.com",
    "[TEAM_MEMBER_5]": "jgoldstein46+5@gmail.com",
    "[TEAM_LEAD]": "jgoldstein46+tl@gmail.com",
    "[FACILITIES_MANAGER]": "jgoldstein46+fm@gmail.com",
    # Add more mappings as needed based on your jira_tickets.json
}

def get_email_from_assignee(assignee_display_name: str) -> str | None:
    """Looks up the email address for a given JIRA assignee display name.

    Args:
        assignee_display_name: The display name from the JIRA ticket's assignee field.

    Returns:
        The corresponding email address string, or None if not found.
    """
    email = ASSIGNEE_EMAIL_MAP.get(assignee_display_name)
    if not email:
        print(f"Warning: Email not found for assignee: {assignee_display_name}")
    return email

if __name__ == '__main__':
    # Example usage for testing
    test_assignees = ["[TEAM_MEMBER_1]", "[TEAM_LEAD]", "Unknown Assignee"]
    for assignee in test_assignees:
        email = get_email_from_assignee(assignee)
        print(f"Assignee: {assignee} -> Email: {email}")

    # Example reading from the JSON file (optional test)
    # try:
    #     with open('data/jira_tickets.json', 'r') as f:
    #         tickets = json.load(f)
    #     if tickets:
    #         # Find the first ticket with an assignee
    #         first_ticket_with_assignee = next((t for t in tickets if t["fields"].get("assignee")), None)
    #         if first_ticket_with_assignee:
    #              first_ticket_assignee = first_ticket_with_assignee["fields"]["assignee"]["displayName"]
    #              print(f"\nTesting with first ticket assignee: {first_ticket_assignee}")
    #              email = get_email_from_assignee(first_ticket_assignee)
    #              print(f"Assignee: {first_ticket_assignee} -> Email: {email}")
    #         else:
    #             print("\nNo tickets found with an assignee for testing.")
    # except FileNotFoundError:
    #     print("\nWarning: data/jira_tickets.json not found for testing.")
    # except Exception as e:
    #     print(f"\nError during JSON test: {e}")
