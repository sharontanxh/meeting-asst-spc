import json
import os
import threading

import requests
from anthropic import Anthropic
from dotenv import load_dotenv
from elevenlabs import play
from elevenlabs.client import ElevenLabs

from tools import ToolManager


class AgentManager:
    """Manages the agent logic and interactions"""

    def __init__(self, callback_status_update=None):
        # Load environment variables
        load_dotenv()

        # API keys - now loaded via load_dotenv()
        self.anthropic_api_key = os.environ["ANTHROPIC_API_KEY"]
        self.elevenlabs_api_key = os.environ["ELEVENLABS_API_KEY"]
        self.voice_id = os.environ["ELEVENLABS_VOICE_ID"]

        # Initialize tool manager
        self.tool_manager = ToolManager()

        # Status update callback
        self.callback_status_update = callback_status_update

        self.anthropic_client = Anthropic(api_key=self.anthropic_api_key)

        self.elevenlabs_client = ElevenLabs(api_key=self.elevenlabs_api_key)

        # Track current active speech thread and add a lock for thread synchronization
        self.active_speech_thread = None
        self.speech_lock = threading.Lock()

        self.system_prompt = """
            ### Role
            You are a helpful meeting assistant named Alex.
            ### Personality
            You are calm, proactive, and highly intelligent with a world-class engineering background. You are witty, relaxed, and effortlessly balance professionalism with an approachable vibe.
            You're naturally curious, diligent, and intuitive, aiming to understand the user's intent and summarizing details that were previously shared.
            ### Environment
            The users are busy ops and technical employees who want direction and actionable tasks. You have access to previous meeting transcripts as well as jira tickets and can reference specific portions to enhance your response. 
            
            Help them reflect on previous issues. In particular, if they are bringing up an issue you should search your knowledge base to look for that issue or topic, and then use the results of that search to inform your reply to the team. 
            
            For example, if the team is talking about a problem with the water cooler, you would search your knowledge base for information about that topic, "water cooler", and see that it has come up in a previous meeting two weeks prior, as well as a month ago. You would also see that there is a pending jira ticket that is regarding that issue. You would reference both of these in your response, highlighting that the water cooler has been pending and who is responsible for it. Be sure to mention any relevant dates in the tickets you find, as well as from meeting transcripts and suggest follow up actions using the tools you have available (e.g. creating a jira ticket, etc.). 
            
            All information must be conveyed clearly through speech.
            ### Tone
            Your responses are concise and measured.
            You speak with thoughtful, but decisive pacing.
            You naturally include conversational elements like "got it, you know."
            ### Goal
            Your primary goal is to guide users to successful completion of tasks and overall team effectiveness.
            """

    def load_transcript_from_file(self, file_path="transcript.txt"):
        """Load a meeting transcript from a file for debugging purposes"""
        try:
            if not os.path.exists(file_path):
                error_msg = f"Error: Transcript file not found at {file_path}"
                print(error_msg)
                if self.callback_status_update:
                    self.callback_status_update(error_msg, "red")
                return None

            with open(file_path, "r") as file:
                transcript = file.read()

            print(f"Loaded transcript from {file_path} ({len(transcript)} characters)")
            if self.callback_status_update:
                self.callback_status_update(f"Loaded debug transcript", "blue")
            return transcript
        except Exception as e:
            error_msg = f"Error loading transcript: {str(e)}"
            print(error_msg)
            if self.callback_status_update:
                self.callback_status_update(error_msg, "red")
            return None

    def run_agent(self, transcript):
        """Run the agent with the meeting transcript context"""
        # Add this check to ensure client exists before proceeding
        if not self.anthropic_client:
            print("Anthropic client not initialized (check API key). Cannot run agent.")
            if self.callback_status_update:
                self.callback_status_update("Error: Anthropic client missing", "red")
            return

        try:
            # Update status
            if self.callback_status_update:
                self.callback_status_update("Agent Processing...", "blue")

            # Prepare initial messages for Claude API

            user_message = f"Here's the transcript of our meeting so far:\n\n{transcript}\n\nCheck for the most recent message asking for your help and respond to it."
            initial_messages = [{"role": "user", "content": user_message}]

            # Define tools for the API call
            tools = [
                {
                    "name": "search_knowledge",
                    "description": """Search for previous context about a particular issue or topic. This knowledge base includes previous meetings as well as jira tickets.""",
                    "input_schema": {
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"],
                    },
                },
                {
                    "name": "create_jira_ticket",
                    "description": """Create a new Jira ticket to track an issue, task, or action item.""",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "summary": {
                                "type": "string",
                                "description": "The summary/title of the ticket",
                            },
                            "description": {
                                "type": "string",
                                "description": "The detailed description of the ticket",
                            },
                            "issue_type": {
                                "type": "string",
                                "description": "The type of issue (e.g., 'Task', 'Bug', 'Story')",
                                "default": "Task",
                            },
                            "labels": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of labels to add to the ticket",
                            },
                            "assignee": {
                                "type": "string",
                                "description": "Account ID or email of the user to assign the ticket to",
                            },
                        },
                        "required": ["project_key", "summary", "description"],
                    },
                },
            ]

            # Call Claude API using the SDK
            response = self.anthropic_client.messages.create(
                model="claude-3-5-haiku-20241022",  # Changed to Haiku
                max_tokens=1024,
                system=self.system_prompt,
                messages=initial_messages,
                tools=tools,
                tool_choice={"type": "auto"},  # Let Claude decide when to use tools
            )
            # --- Log Claude Response ---
            print("--- Claude Initial Response ---")
            # Iterate through content blocks and log only text/tool use
            if response and hasattr(
                response, "content"
            ):  # Check if response and content exist
                for content_block in response.content:
                    if content_block.type == "text":
                        print(f"[Claude Text]: {content_block.text}")
                    elif content_block.type == "tool_use":
                        print(
                            f"[Claude Tool Use]: Name={content_block.name}, Input={content_block.input}"
                        )
            else:
                print(
                    "[Log Warning] Could not parse Claude response content for simplified logging."
                )
                print(str(response))
            print("-----------------------------")
            # --- End Log ---

            # Process response (check for tool calls or text)
            final_text = self._process_claude_response(
                response, initial_messages, tools
            )

            # Generate and play speech if text is available
            if final_text:
                if self.callback_status_update:
                    self.callback_status_update("Agent Speaking...", "blue")
                self._generate_and_play_speech(final_text)
            else:
                print("Agent finished but produced no text response.")

            # Update status when complete
            if self.callback_status_update:
                self.callback_status_update("Agent Complete", "green")

        except Exception as e:
            print(f"Agent error: {e}")
            if self.callback_status_update:
                self.callback_status_update(f"Error: {str(e)[:30]}...", "red")

    def _process_claude_response(self, response, current_messages, tools):
        """Process the Claude response, handling tool calls if necessary."""

        # Process this response and any follow-up responses with tool calls
        def process_response(response, messages, accumulated_text=""):
            tool_calls_made = False
            search_knowledge_called = False
            response_text = ""
            assistant_responses = []

            # Process content blocks in the response
            for content_block in response.content:
                if content_block.type == "text":
                    response_text += content_block.text
                    assistant_responses.append(
                        {"role": "assistant", "content": content_block.text}
                    )
                elif content_block.type == "tool_use":
                    tool_calls_made = True
                    # Check if search_knowledge was called
                    if content_block.name == "search_knowledge":
                        search_knowledge_called = True

                    # Add tool request to messages for context in follow-up
                    assistant_responses.append(
                        {
                            "role": "assistant",
                            "content": [
                                {
                                    "type": "tool_use",
                                    "id": content_block.id,
                                    "name": content_block.name,
                                    "input": content_block.input,
                                }
                            ],
                        }
                    )

            # Add assistant responses to message history
            messages.extend(assistant_responses)

            # Play speech for the current response text if it exists
            if response_text.strip():
                self._generate_and_play_speech_async(response_text)

            # If no tool calls, return the accumulated text plus this response's text
            if not tool_calls_made:
                return accumulated_text + response_text, messages

            # --- Handle Tool Calls ---
            print("Agent requested tool usage...")
            if self.callback_status_update:
                self.callback_status_update("Agent Using Tools...", "blue")

            tool_results_content = []

            # Process the tools silently without announcing them
            for content_block in response.content:
                if content_block.type == "tool_use":
                    tool_name = content_block.name
                    tool_input = content_block.input
                    tool_call_id = content_block.id

                    # Execute the tool
                    print(f"Executing tool: {tool_name} with input: {tool_input}")
                    tool_result = self.tool_manager.execute_tool(tool_name, tool_input)
                    print(f"Tool result: {tool_result}")

                    # Append tool result for the next API call
                    tool_results_content.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_call_id,
                            "content": tool_result,  # The result is already a JSON string
                        }
                    )

            # Add the tool results message to the history
            messages.append({"role": "user", "content": tool_results_content})

            # Only continue recursion if search_knowledge was called
            if not search_knowledge_called:
                print("Non-search_knowledge tool used, stopping recursion")
                return accumulated_text + response_text, messages

            # Call Claude again with the tool results
            print("Calling Claude again with tool results...")
            follow_up_response = self.anthropic_client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=1024,
                system=self.system_prompt,
                messages=[msg for msg in messages if msg["role"] != "system"],
                tools=tools,
            )

            # --- Log Claude Follow-up Response ---
            print("--- Claude Follow-up Response ---")
            try:
                print(follow_up_response.model_dump_json(indent=2))
            except AttributeError:  # Fallback if model_dump_json doesn't exist
                print(str(follow_up_response))
            print("-------------------------------")

            # Recursively process the follow-up response to handle any additional tool calls
            return process_response(follow_up_response, messages, accumulated_text)

        # Start the recursive processing with the initial response
        final_text, _ = process_response(response, current_messages)

        # Wait for any final speech to complete before returning
        if self.active_speech_thread and self.active_speech_thread.is_alive():
            self.active_speech_thread.join()

        return final_text.strip()

    def _generate_and_play_speech_async(self, text):
        """Generate speech from text and play it in a background thread, waiting for any previous speech to finish"""
        with self.speech_lock:
            # Wait for any active speech thread to complete first
            if self.active_speech_thread and self.active_speech_thread.is_alive():
                print("Waiting for previous speech to complete")
                self.active_speech_thread.join()

            # Create and start a new thread
            thread = threading.Thread(target=self._speech_worker, args=(text,))
            thread.daemon = (
                True  # Make thread a daemon so it doesn't block program exit
            )
            thread.start()
            self.active_speech_thread = thread

    def _speech_worker(self, text):
        """Worker function that runs in a background thread to generate and play speech"""
        if not self.elevenlabs_client:
            print("ElevenLabs client not initialized. Skipping speech generation.")
            print(f"Agent response (text only): {text}")
            return

        try:
            # Generate audio using the client's method
            audio = self.elevenlabs_client.text_to_speech.convert(
                text=text,
                voice_id=self.voice_id,
                model_id="eleven_multilingual_v2",
            )

            # Play the audio
            play(audio)

        except Exception as e:
            print(f"Speech generation error: {e}")
            # Fallback to print
            print(f"Agent response: {text}")

    def _generate_and_play_speech(self, text):
        """Legacy synchronous method for completeness"""
        return self._speech_worker(text)
