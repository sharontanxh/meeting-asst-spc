import json
import requests
import os
from elevenlabs import play
from elevenlabs.client import ElevenLabs
from tools import ToolManager
from dotenv import load_dotenv
from anthropic import Anthropic

class AgentManager:
    """Manages the agent logic and interactions"""
    
    def __init__(self, callback_status_update=None):
        # Load environment variables
        load_dotenv()
        
        # API keys - now loaded via load_dotenv()
        self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "your_api_key_here")
        self.elevenlabs_api_key = os.environ.get("ELEVENLABS_API_KEY", "your_api_key_here")
        self.voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "default_voice_id")
        
        # Initialize tool manager
        self.tool_manager = ToolManager()
        
        # Status update callback
        self.callback_status_update = callback_status_update

        # Initialize Anthropic client
        if self.anthropic_api_key and self.anthropic_api_key != "your_api_key_here":
            self.anthropic_client = Anthropic(api_key=self.anthropic_api_key)
        else:
            print("Warning: Anthropic API key not found or is default. Agent calls will fail.")
            self.anthropic_client = None

        # Initialize ElevenLabs client
        if self.elevenlabs_api_key and self.elevenlabs_api_key != "your_api_key_here":
             self.elevenlabs_client = ElevenLabs(api_key=self.elevenlabs_api_key)
        else:
             print("Warning: ElevenLabs API key not found or is default. Speech generation will likely fail.")
             self.elevenlabs_client = None # Set client to None if key is missing
    
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
            system_prompt = """
            ### Role
            You are a helpful meeting assistant.
            ### Personality
            You are calm, proactive, and highly intelligent with a world-class engineering background. You are witty, relaxed, and effortlessly balance professionalism with an approachable vibe.
            You're naturally curious, diligent, and intuitive, aiming to understand the user's intent and summarizing details that were previously shared.
            ### Environment
            The users are busy ops and technical employees who want direction and actionable tasks. You have access to previous meeting transcripts and can reference specific portions to enhance your response.All information must be conveyed clearly through speech.
            ### Tone
            Your responses are concise, measured, and typically 1-2 sentences.
            You speak with thoughtful, but decisive pacing.
            You naturally include conversational elements like "got it, you know."
            ### Goal
            Your primary goal is to guide users to successful completion of tasks and overall team effectiveness.
            """
            user_message = f"Here's the transcript of our meeting so far:\n\n{transcript}\n\nCheck for the most recent message asking for your help and respond to it."
            initial_messages = [
                {"role": "user", "content": user_message}
            ]

            # Define tools for the API call
            tools = [
                    {
                        "name": "search_jira",
                        "description": "Search for JIRA tickets",
                        "input_schema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"}
                            },
                            "required": ["query"]
                        }
                    },
                    {
                        "name": "create_calendar_event",
                        "description": "Create a calendar event",
                        "input_schema": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "start_time": {"type": "string"},
                                "duration_minutes": {"type": "integer"}
                            },
                            "required": ["title", "start_time"]
                        }
                    },
                    {
                        "name": "query_vector_db",
                        "description": "Search the vector database for related previous meeting transcripts and jira tickets",
                        "input_schema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"}
                            },
                            "required": ["query"]
                        }
                    }
                ]
            
            # Call Claude API using the SDK
            response = self.anthropic_client.messages.create(
                model="claude-3-5-haiku-20241022", # Changed to Haiku
                max_tokens=1024,
                system=system_prompt,
                messages=initial_messages,
                tools=tools,
                tool_choice={"type": "auto"} # Let Claude decide when to use tools
            )
            # --- Log Claude Response ---
            print("--- Claude Initial Response ---")
            # Iterate through content blocks and log only text/tool use
            if response and hasattr(response, 'content'): # Check if response and content exist
                for content_block in response.content:
                    if content_block.type == "text":
                        print(f"[Claude Text]: {content_block.text}")
                    elif content_block.type == "tool_use":
                        print(f"[Claude Tool Use]: Name={content_block.name}, Input={content_block.input}")
            else:
                print("[Log Warning] Could not parse Claude response content for simplified logging.")
                print(str(response))
            print("-----------------------------")
            # --- End Log ---
            
            # Process response (check for tool calls or text)
            final_text = self._process_claude_response(response, initial_messages, tools)
            
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
        final_text = ""
        tool_calls_made = False
        
        # Add assistant's initial response (might include tool requests)
        assistant_responses = []
        for content_block in response.content:
            if content_block.type == "text":
                assistant_responses.append({"role": "assistant", "content": content_block.text})
                final_text += content_block.text # Capture initial text
            elif content_block.type == "tool_use":
                tool_calls_made = True
                # Add tool request to messages for context in follow-up
                assistant_responses.append({
                    "role": "assistant", 
                    "content": [{
                        "type": "tool_use",
                        "id": content_block.id,
                        "name": content_block.name,
                        "input": content_block.input
                    }]
                })
        
        # Add assistant responses to message history
        current_messages.extend(assistant_responses)

        # If no tool calls, return the text we already gathered
        if not tool_calls_made:
            return final_text.strip()
            
        # --- Handle Tool Calls --- 
        print("Agent requested tool usage...")
        if self.callback_status_update:
             self.callback_status_update("Agent Using Tools...", "blue")
             
        tool_results_content = []
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
                 tool_results_content.append({
                     "type": "tool_result",
                     "tool_use_id": tool_call_id,
                     "content": json.dumps(tool_result) # Ensure result is JSON string
                 })

        # Add the tool results message to the history
        current_messages.append({
            "role": "user",
            "content": tool_results_content
        })

        # Call Claude again with the tool results
        print("Calling Claude again with tool results...")
        follow_up_response = self.anthropic_client.messages.create(
            model="claude-3-5-haiku-20241022", # Changed to Haiku
            max_tokens=1024,
            system=current_messages[0]["content"] if current_messages[0]["role"] == "system" else None, # Reuse system prompt if present
            messages=[msg for msg in current_messages if msg["role"] != "system"], # Send message history (excluding system)
            tools=tools # Provide tools again just in case?
        )
        
        # --- Log Claude Follow-up Response ---
        print("--- Claude Follow-up Response ---")
        try:
            print(follow_up_response.model_dump_json(indent=2))
        except AttributeError: # Fallback if model_dump_json doesn't exist
            print(str(follow_up_response))
        print("-------------------------------")
        # --- End Log ---

        # Extract final text from the follow-up response
        final_text = ""
        for content_block in follow_up_response.content:
             if content_block.type == "text":
                 final_text += content_block.text

        return final_text.strip()

    def _generate_and_play_speech(self, text):
        """Generate speech from text and play it"""
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