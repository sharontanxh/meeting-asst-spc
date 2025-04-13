import json

def create_meeting_map(input_file: str, output_file: str):
    with open(input_file, 'r') as file:
        content = file.read()

    # Split the content into meetings based on the "### Meeting" header
    meetings = content.split("### Meeting")
    meeting_map = {}

    for meeting in meetings[1:]:  # Skip the first split part which is before the first meeting
        lines = meeting.strip().splitlines()
        if lines:
            # The first line is the meeting title
            title = lines[0].strip()
            # The rest is the meeting content
            text = "\n".join(lines[1:]).strip()
            # Create a key for the meeting
            meeting_key = title.lower().replace(" ", "-").replace(":", "").replace(",", "")
            meeting_map[meeting_key] = text

    # Write the meeting map to a new JSON file
    with open(output_file, 'w') as json_file:
        json.dump(meeting_map, json_file, indent=2)

# Usage
create_meeting_map('data/meeting_transcripts.txt', 'data/meeting_map.json')