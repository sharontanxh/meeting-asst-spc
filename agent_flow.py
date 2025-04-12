import json
import requests
import os
from elevenlabs import generate, play, Voice
from tools import ToolManager
from dotenv import load_dotenv

class AgentManager:
    """Manages the agent logic and interactions"""
    
    def __init__(self, callback_status_update=None):
        # Load environment variables
        load_dotenv()
        
        # API keys - now loaded via load_dotenv()
        self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
        self.elevenlabs_api_key = os.environ.get("ELEVENLABS_API_KEY")
        self.voice_id = os.environ.get("ELEVENLABS_VOICE_ID")
        
        # Initialize tool manager
        self.tool_manager = ToolManager()
        
        # Status update callback
        self.callback_status_update = callback_status_update
    
    def run_agent(self, transcript):
        """Run the agent with the meeting transcript context"""
        try:
            # Update status
            if self.callback_status_update:
                self.callback_status_update("Agent Processing...", "blue")
            
            # Call Claude API
            response = self._call_claude_api(transcript)
            
            # Process tool calls if present
            if "tool_calls" in response:
                final_response = self._process_tool_calls(response, transcript)
            else:
                final_response = response
            
            # Get the final text response
            final_text = final_response["content"][0]["text"]
            
            # Generate and play speech
            if self.callback_status_update:
                self.callback_status_update("Agent Speaking...", "blue")
                
            self._generate_and_play_speech(final_text)
            
            # Update status when complete
            if self.callback_status_update:
                self.callback_status_update("Agent Complete", "green")
                
        except Exception as e:
            print(f"Agent error: {e}")
            if self.callback_status_update:
                self.callback_status_update(f"Error: {str(e)[:30]}...", "red")
    
    def _call_claude_api(self, transcript):
        """Call the Claude API with the transcript context"""
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.anthropic_api_key,
                "anthropic-version": "2023-06-01"
            },
            json={
                "model": "claude-3-sonnet-20240229",
                "max_tokens": 1024,
                "messages": [
                    {
                        "role": "system", 
                        "content": "You are a helpful meeting assistant. You'll receive a meeting transcript and may need to use tools to help the participants."
                    },
                    {
                        "role": "user", 
                        "content": f"Here's the transcript of our meeting so far:\n\n{transcript}\n\nBased on this, can you help us with any action items or questions?"
                    }
                ],
                "tools": [
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
                        "description": "Search the vector database for related information",
                        "input_schema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"}
                            },
                            "required": ["query"]
                        }
                    }
                ]
            }
        )
        
        return response.json()
    
    def _process_tool_calls(self, response, transcript):
        """Process any tool calls in the response"""
        messages = [
            {"role": "system", "content": "You are a helpful meeting assistant."},
            {"role": "user", "content": f"Meeting transcript: {transcript}"},
            {"role": "assistant", "content": response["content"][0]["text"]}
        ]
        
        # Process each tool call
        for tool_call in response["tool_calls"]:
            tool_name = tool_call["name"]
            tool_args = tool_call["input"]
            
            # Execute the tool
            tool_result = self.tool_manager.execute_tool(tool_name, tool_args)
            
            # Add the tool result to messages
            messages.append(
                {"role": "tool", "name": tool_name, "content": json.dumps(tool_result)}
            )
        
        # Add final user message
        messages.append(
            {"role": "user", "content": "Please continue helping with the meeting."}
        )
        
        # Call Claude again with the tool results
        follow_up_response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.anthropic_api_key,
                "anthropic-version": "2023-06-01"
            },
            json={
                "model": "claude-3-sonnet-20240229",
                "max_tokens": 1024,
                "messages": messages
            }
        )
        
        return follow_up_response.json()
    
    def _generate_and_play_speech(self, text):
        """Generate speech from text and play it"""
        try:
            from elevenlabs import generate, play, Voice
            
            # Generate audio
            audio = generate(
                text=text,
                voice=Voice(voice_id=self.voice_id),
                model="eleven_multilingual_v2",
                api_key=self.elevenlabs_api_key
            )
            
            # Play the audio
            play(audio)
            
        except Exception as e:
            print(f"Speech generation error: {e}")
            # Fallback to print
            print(f"Agent response: {text}")