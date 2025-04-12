import json
import requests
from datetime import datetime, timedelta

class ToolManager:
    """Manages tool implementations for the agent"""
    
    def __init__(self, config=None):
        self.config = config or {}
        
    def execute_tool(self, tool_name, tool_args):
        """Route tool calls to the appropriate implementation"""
        if tool_name == "search_jira":
            return self.search_jira(tool_args["query"])
        elif tool_name == "create_calendar_event":
            return self.create_calendar_event(
                tool_args["title"],
                tool_args["start_time"],
                tool_args.get("duration_minutes", 30)
            )
        elif tool_name == "query_vector_db":
            return self.query_vector_db(tool_args["query"])
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    
    def search_jira(self, query):
        """Search for JIRA tickets"""
        print(f"Searching JIRA for: {query}")
        
        # In a real implementation, you would make an API call to JIRA
        # For the hackathon, we can simulate the response
        return {
            "tickets": [
                {"id": "PROJ-123", "title": "Implement meeting assistant", "status": "In Progress"},
                {"id": "PROJ-124", "title": "Fix transcription accuracy", "status": "Todo"},
                {"id": "PROJ-125", "title": "Add more tools", "status": "Backlog"}
            ]
        }
    
    def create_calendar_event(self, title, start_time, duration_minutes=30):
        """Create a calendar event"""
        print(f"Creating calendar event: {title} at {start_time}")
        
        # In a real implementation, you would make an API call to your calendar system
        # For the hackathon, we can simulate the response
        return {
            "success": True,
            "event_id": f"event_{hash(title) % 10000}",
            "details": {
                "title": title,
                "start_time": start_time,
                "end_time": self._calculate_end_time(start_time, duration_minutes),
                "duration_minutes": duration_minutes
            }
        }
    
    def query_vector_db(self, query):
        """Search a vector database for similar content"""
        print(f"Searching vector DB for: {query}")
        
        # In a real implementation, you would query your vector database
        # For the hackathon, we can simulate the response
        return {
            "results": [
                {
                    "text": "In yesterday's meeting we decided to focus on the agent implementation first.",
                    "score": 0.92,
                    "source": "meeting_2024-04-11.txt"
                },
                {
                    "text": "The team agreed that integrating with JIRA is a priority for next sprint.",
                    "score": 0.85,
                    "source": "meeting_2024-04-10.txt"
                }
            ]
        }
    
    def _calculate_end_time(self, start_time, duration_minutes):
        """Helper to calculate end time from start time and duration"""
        try:
            start = datetime.fromisoformat(start_time)
            end = start + timedelta(minutes=duration_minutes)
            return end.isoformat()
        except ValueError:
            # Handle non-ISO format times
            return f"start_time + {duration_minutes} minutes"