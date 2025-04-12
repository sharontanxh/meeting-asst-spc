#!/usr/bin/env python3

import json
import os
import requests
from requests.auth import HTTPBasicAuth
import sys
from dotenv import load_dotenv

# --- Configuration ---
# Load sensitive information from environment variables
# You MUST set these environment variables before running the script:
# export JIRA_DOMAIN="your-domain.atlassian.net"
# export JIRA_EMAIL="your-email@example.com"
# export JIRA_API_TOKEN="your_api_token_here"
load_dotenv()
JIRA_DOMAIN = os.getenv("JIRA_DOMAIN")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JSON_FILE_PATH = "/Users/sharontan/Documents/Personal/meeting-assistant/data/jira_tickets.json" # Relative path to the data file

# --- Mappings (YOU NEED TO UPDATE THESE) ---

# Map placeholder names to actual Jira Account IDs
# Find Account IDs via Jira UI (User Profile URL) or API (/rest/api/3/user/search)
USER_ACCOUNT_ID_MAP = {
    "[TEAM_MEMBER_1]": "712020:5ca938f6-d6f6-4d5e-99d9-d0a19189088c",
    "[TEAM_MEMBER_2]": "70121:18055ba5-fd51-4fed-8a39-57913127d239",
    "[TEAM_MEMBER_3]": "70121:d5434616-342f-4b95-88cc-c3e14fd9b4ff",
    "[TEAM_MEMBER_4]": "712020:5646fa79-3b04-4e3b-8b1a-dea09ccbdb7a",
    "[TEAM_MEMBER_5]": "640a68ec0d9b61193c288899",
    "[TEAM_LEAD]": "712020:3afa6d9b-4446-4c96-94ec-84f65f435ef0",
    "[FACILITIES_MANAGER]": "70121:d5434616-342f-4b95-88cc-c3e14fd9b4ff",
    # Add any other placeholder names found in your JSON
}

# Verify these custom field IDs in your Jira instance.
# Find them via Project Settings -> Issues -> Custom Fields, or API (/rest/api/3/field)
# The format needed for the API call might depend on the field type (e.g., { "value": "XYZ" } for a text field)
# You might need to adjust the format in the build_payload function.
# For now, we assume they accept simple string/number values.


# --- Helper Functions ---

def load_tickets(file_path):
    """Loads tickets from the JSON file."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: JSON file not found at {file_path}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {file_path}")
        sys.exit(1)

def get_account_id(display_name):
    """Maps display name to Jira Account ID."""
    account_id = USER_ACCOUNT_ID_MAP.get(display_name)
    if not account_id or "replace_with" in account_id:
        print(f"Warning: No valid Account ID found for '{display_name}'. Skipping assignment.")
        return None
    return {"accountId": account_id}

def build_payload(ticket_data):
    """Builds the payload for the Jira API create issue request."""
    fields = ticket_data.get("fields", {})
    
    # Map Assignee and Reporter
    assignee_name = fields.get("assignee", {}).get("displayName")
    reporter_name = fields.get("reporter", {}).get("displayName")
    
    assignee_payload = get_account_id(assignee_name) if assignee_name else None
    reporter_payload = get_account_id(reporter_name) if reporter_name else None

    # Basic fields (ensure names match your Jira config)
    payload_fields = {
        "project": {"key": fields.get("project", {}).get("key")},
        "summary": fields.get("summary"),
        "description": { # Jira expects description in ADF (Atlassian Document Format) or plain text
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": fields.get("description", "")
                        }
                    ]
                }
            ]
        },
        "issuetype": {"name": fields.get("issuetype", {}).get("name")},
        # "priority": {"name": fields.get("priority", {}).get("name")},
        "labels": fields.get("labels", [])
    }

    # Add assignee and reporter only if successfully mapped
    if assignee_payload:
        payload_fields["assignee"] = assignee_payload
    if reporter_payload:
        payload_fields["reporter"] = reporter_payload # Note: Often reporter is set to the API user by default if not provided

    # Add duedate if present
    # if fields.get("duedate"):
    #     payload_fields["duedate"] = fields.get("duedate") # Assumes YYYY-MM-DD format

    # Add custom fields (adjust format based on actual field type if needed)


    # Clean out any None values from the payload fields
    payload_fields = {k: v for k, v in payload_fields.items() if v is not None}

    return {"fields": payload_fields}

def create_jira_ticket(payload, domain, email, token):
    """Sends the request to create a ticket in Jira."""
    api_url = f"https://{domain}/rest/api/3/issue"
    auth = HTTPBasicAuth(email, token)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    response = requests.post(api_url, headers=headers, auth=auth, json=payload)
    
    if response.status_code == 201:
        print(f"Success: Created ticket {response.json()['key']} - Summary: {payload['fields']['summary']}")
        return response.json()
    else:
        print(f"Error creating ticket: {response.status_code} - Summary: {payload['fields']['summary']}")
        print(f"Response: {response.text}")
        return None

# --- Main Execution ---

def main():
    # Validate environment variables
    if not all([JIRA_DOMAIN, JIRA_EMAIL, JIRA_API_TOKEN]):
        print("Error: Missing required environment variables (JIRA_DOMAIN, JIRA_EMAIL, JIRA_API_TOKEN).")
        print("Please set them and try again.")
        sys.exit(1)
        
    print("Starting Jira ticket upload...")
    print(f"Loading tickets from: {JSON_FILE_PATH}")
    
    tickets_to_upload = load_tickets(JSON_FILE_PATH)
    print(f"Found {len(tickets_to_upload)} tickets to potentially upload.")
    
    # --- !!! SAFETY CHECK - COMMENT OUT FOR ACTUAL RUN !!! ---
    print("""
--- DRY RUN MODE ---
Script will print payloads but NOT create tickets.
Review payloads and mappings carefully.
Comment out the 'dry_run = True' line and the sys.exit() below it to run for real.
""")
    dry_run = False
    # sys.exit("Exiting after dry run.") # Uncomment to force exit after dry run
    # --- !!! END SAFETY CHECK !!! ---
    
    created_count = 0
    error_count = 0

    for i, ticket in enumerate(tickets_to_upload):
        print(f"Processing ticket {i+1}/{len(tickets_to_upload)} (Original ID: {ticket.get('id')})")
        payload = build_payload(ticket)
        
        if dry_run:
            print("Payload:")
            print(json.dumps(payload, indent=2))
            # Optionally add checks here in dry run mode
            if not payload["fields"].get("project", {}).get("key"):
                 print("Error: Project key missing in payload.")
            if not payload["fields"].get("summary"):
                 print("Error: Summary missing in payload.")
            if not payload["fields"].get("issuetype", {}).get("name"):
                 print("Error: Issue type missing in payload.")
            continue # Skip API call in dry run

        # --- Actual API Call ---
        # print("Attempting to create ticket...") # Uncomment for verbose real run
        result = create_jira_ticket(payload, JIRA_DOMAIN, JIRA_EMAIL, JIRA_API_TOKEN)
        if result:
            created_count += 1
        else:
            error_count += 1
            
        # Optional: Add a small delay between requests if needed
        # import time
        # time.sleep(0.5) 

    print("\n--- Upload Summary ---")
    if dry_run:
        print("Dry run completed. No tickets were created.")
    else:
        print(f"Tickets successfully created: {created_count}")
        print(f"Tickets failed to create: {error_count}")

if __name__ == "__main__":
    main()
