import tkinter as tk
import threading
import time
from dotenv import load_dotenv
from transcription import TranscriptionManager
from agent_flow import AgentManager

class MeetingAssistantApp:
    def __init__(self, root):
        # Initialize the main window
        self.root = root
        self.root.title("Meeting Assistant")
        self.root.geometry("400x300")
        
        # Global state
        self.meeting_transcript = ""
        
        # Initialize managers
        self.transcription_manager = TranscriptionManager(
            callback_new_text=self.on_new_transcript
        )
        self.agent_manager = AgentManager(
            callback_status_update=self.update_status
        )
        
        # Set up UI
        self.setup_ui()
    
    def setup_ui(self):
        # Status display
        status_frame = tk.Frame(self.root)
        status_frame.pack(pady=10)
        
        self.status_label = tk.Label(status_frame, text="Not Transcribing", fg="red", font=("Arial", 12))
        self.status_label.pack()
        
        # Create buttons
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=20)
        
        self.transcription_button = tk.Button(
            button_frame, 
            text="Start Transcribing", 
            command=self.toggle_transcription
        )
        self.transcription_button.grid(row=0, column=0, padx=10)
        
        self.agent_button = tk.Button(
            button_frame, 
            text="Activate Agent", 
            command=self.activate_agent
        )
        self.agent_button.grid(row=0, column=1, padx=10)
        
        self.resume_button = tk.Button(
            button_frame, 
            text="Resume Transcription",
            command=self.resume_transcription
        )
        self.resume_button.grid(row=0, column=2, padx=10)
    
    def toggle_transcription(self):
        """Toggle transcription on/off"""
        if self.transcription_manager.is_transcribing:
            self.transcription_manager.stop_transcription()
            self.transcription_button.config(text="Start Transcribing")
            self.status_label.config(text="Not Transcribing", fg="red")
        else:
            self.transcription_manager.start_transcription()
            self.transcription_button.config(text="Stop Transcribing")
            self.status_label.config(text="Transcribing...", fg="green")
    
    def on_new_transcript(self, new_text):
        """Callback when new transcript text is available"""
        self.meeting_transcript += new_text
    
    def activate_agent(self):
        """Activate the agent with the current transcript"""
        # Store current state
        was_transcribing = self.transcription_manager.is_transcribing
        
        # Pause transcription if running
        if was_transcribing:
            self.transcription_manager.stop_transcription()
            self.transcription_button.config(text="Start Transcribing")
            
        # Update status
        self.status_label.config(text="Agent Active", fg="blue")
        
        # Run agent in a separate thread
        agent_thread = threading.Thread(
            target=lambda: self.agent_manager.run_agent(self.meeting_transcript)
        )
        agent_thread.daemon = True
        agent_thread.start()
    
    def resume_transcription(self):
        """Resume transcription after agent completes"""
        if not self.transcription_manager.is_transcribing:
            self.transcription_manager.start_transcription()
            self.transcription_button.config(text="Stop Transcribing")
            self.status_label.config(text="Transcribing...", fg="green")
    
    def update_status(self, status_text, color="black"):
        """Update the status label from other threads"""
        self.root.after(0, lambda: self.status_label.config(text=status_text, fg=color))

def main():
    # Load environment variables from .env file
    load_dotenv()
    
    # Create the main window
    root = tk.Tk()
    
    # Create the app
    app = MeetingAssistantApp(root)
    
    # Start the UI event loop
    root.mainloop()

if __name__ == "__main__":
    main()