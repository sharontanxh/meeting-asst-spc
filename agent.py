import os
import signal

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs.conversational_ai.conversation import ClientTools, Conversation
from elevenlabs.conversational_ai.default_audio_interface import DefaultAudioInterface

from jira_comment import add_jira_comment
from jira_ticket import create_jira_ticket

load_dotenv()

agent_id: str = os.environ["AGENT_ID"]
api_key: str = os.environ["ELEVENLABS_API_KEY"]


client = ElevenLabs(api_key=api_key)


def add_jira_comment_tool(parameters):
    ticket_key = parameters.get("ticket_key")
    comment = parameters.get("comment")
    try:
        result = add_jira_comment(ticket_key, comment)
        return {"success": True, "message": f"Comment added to {ticket_key}"}
    except Exception as e:
        return {"success": False, "message": str(e)}


def create_jira_ticket_tool(parameters):
    project_key = parameters.get("project_key")
    summary = parameters.get("summary")
    description = parameters.get("description")
    issue_type = parameters.get("issue_type", "Task")
    labels = parameters.get("labels", [])

    try:
        result = create_jira_ticket(
            project_key=project_key,
            summary=summary,
            description=description,
            issue_type=issue_type,
            labels=labels,
        )
        return result
    except Exception as e:
        return {"success": False, "message": str(e)}


client_tools = ClientTools()

client_tools.register("addJiraComment", add_jira_comment_tool)
client_tools.register("createJiraTicket", create_jira_ticket_tool)

conversation = Conversation(
    # API client and agent ID.
    client,
    agent_id,
    # Assume auth is required when API_KEY is set.
    requires_auth=bool(api_key),
    # Use the default audio interface.
    audio_interface=DefaultAudioInterface(),
    # Simple callbacks that print the conversation to the console.
    callback_agent_response=lambda response: print(f"Agent: {response}"),
    callback_agent_response_correction=lambda original, corrected: print(
        f"Agent: {original} -> {corrected}"
    ),
    callback_user_transcript=lambda transcript: print(f"User: {transcript}"),
    client_tools=client_tools,
    # Uncomment if you want to see latency measurements.
    # callback_latency_measurement=lambda latency: print(f"Latency: {latency}ms"),
)

conversation.start_session()

signal.signal(signal.SIGINT, lambda sig, frame: conversation.end_session())

conversation_id = conversation.wait_for_session_end()
print(f"Conversation ID: {conversation_id}")
