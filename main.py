import os
import glob
import threading
import time
from dotenv import load_dotenv
import customtkinter as ctk
from transcription import ElevenLabsTranscriptionManager as TranscriptionManager
from agent_flow import AgentManager

# Define Icons
ICON_START = "🎙️"
ICON_STOP = "⏹️"
ICON_AGENT = "✨"

# Define Status Indicator Characters
STATUS_RED = "🔴"
STATUS_GREEN = "🟢"
STATUS_BLUE = "🔵"
STATUS_BLACK = "⚫"

class MeetingAssistantApp:
    def __init__(self, root):
        # Initialize the main window
        self.root = root
        self.root.title("Alex")
        
        # Set appearance mode and default color theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        
        # Configure window transparency
        self.root.attributes("-alpha", 0.9)  # 90% opacity
        
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
        
        # Resize window to fit content
        self.root.update()
        self.root.minsize(self.root.winfo_width(), self.root.winfo_height())
    
    def setup_ui(self):
        # Main frame with minimal padding
        self.main_frame = ctk.CTkFrame(self.root, corner_radius=15, fg_color="#2D2D2D")
        self.main_frame.pack(fill="both", expand=True, padx=8, pady=8)
        
        # Status display at top
        self.status_label = ctk.CTkLabel(
            self.main_frame, 
            text=f"{STATUS_RED} Not Transcribing",
            font=ctk.CTkFont(family="Helvetica", size=13, weight="bold"),
            text_color="#FFFFFF"
        )
        self.status_label.pack(anchor="center", pady=(10, 5))
        
        # Create buttons in vertical layout
        self.transcription_button = ctk.CTkButton(
            self.main_frame,
            text=f"{ICON_START} Start",
            command=self.toggle_transcription,
            font=ctk.CTkFont(family="Helvetica", size=12),
            corner_radius=10,
            fg_color="#444444",
            hover_color="#555555",
            border_width=1,
            border_color="#666666",
            height=30,
            width=150
        )
        self.transcription_button.pack(pady=(5, 5))
        
        self.agent_button = ctk.CTkButton(
            self.main_frame,
            text=f"{ICON_AGENT} Activate",
            command=self.activate_agent,
            font=ctk.CTkFont(family="Helvetica", size=12),
            corner_radius=10,
            fg_color="#444444",
            hover_color="#555555",
            border_width=1,
            border_color="#666666",
            height=30,
            width=150
        )
        self.agent_button.pack(pady=(0, 10))

    def animate_status(self):
        """Subtle pulsing animation for the status label"""
        # Check every 500ms to update animation based on status
        current_text = self.status_label.cget("text")
        
        # Only apply subtle pulsing effect for active states
        if STATUS_GREEN in current_text or STATUS_BLUE in current_text:
            # Subtle transparency pulse
            current_alpha = self.root.attributes("-alpha")
            new_alpha = 0.85 if current_alpha > 0.88 else 0.9
            self.root.attributes("-alpha", new_alpha)
            
        self.root.after(500, self.animate_status)

    def toggle_transcription(self):
        """Toggle transcription on/off"""
        if self.transcription_manager.is_transcribing:
            self.transcription_manager.stop_transcription()
            self.transcription_button.configure(text=f"{ICON_START} Start")
            self.status_label.configure(text=f"{STATUS_RED} Not Transcribing")
        else:
            self.transcription_manager.start_transcription()
            self.transcription_button.configure(text=f"{ICON_STOP} Stop")
            self.status_label.configure(text=f"{STATUS_GREEN} Transcribing...")

    def on_new_transcript(self, new_text):
        """Callback when new transcript text is available"""
        print(f"[Callback Main] on_new_transcript received text (length {len(new_text)}): '{new_text[:100]}...'")
        self.meeting_transcript += new_text
    
    def activate_agent(self):
        """Activate the agent with the current transcript or latest saved transcript in DEBUG mode."""
        
        transcript_to_use = "" 
        debug_mode = os.environ.get("AGENT_DEBUG_MODE", "").lower() == "true"
        was_transcribing = False

        if debug_mode:
            print("[DEBUG MODE] Agent activated. Loading latest transcript from file.")
            transcript_dir = "data/transcripts" 
            try:
                list_of_files = glob.glob(os.path.join(transcript_dir, "meeting_transcript_*.txt"))
                if not list_of_files:
                    print(f"[DEBUG MODE] No transcript files found in '{transcript_dir}'. Using empty transcript.")
                    transcript_to_use = ""
                else:
                    latest_file = max(list_of_files) 
                    print(f"[DEBUG MODE] Loading transcript from: {latest_file}")
                    with open(latest_file, 'r', encoding='utf-8') as f:
                        transcript_to_use = f.read()
                    print(f"[DEBUG MODE] Loaded transcript length: {len(transcript_to_use)}")
            except Exception as e:
                print(f"[DEBUG MODE] Error loading latest transcript: {e}")
                transcript_to_use = "" 
        else:
            print("Agent activated with live transcript.")
            transcript_to_use = self.meeting_transcript
            
            was_transcribing = self.transcription_manager.is_transcribing
            if was_transcribing:
                print("Pausing live transcription for agent.")
                self.transcription_manager.stop_transcription()
                self.transcription_button.configure(text=f"{ICON_START} Start")
            
        self.status_label.configure(text=f"{STATUS_BLUE} Agent Active")
        
        print(f"Activating agent with transcript (length {len(transcript_to_use)}):")
        print(f"'{transcript_to_use[:500]}{'...' if len(transcript_to_use) > 500 else ''}'") 

        agent_thread = threading.Thread(
            target=lambda: self.agent_manager.run_agent(transcript_to_use)
        )
        agent_thread.daemon = True
        agent_thread.start()
    
    def update_status(self, status_text, color="black"):
        """Update the status label from other threads using icons"""
        status_map = {
            "red": STATUS_RED,
            "green": STATUS_GREEN,
            "blue": STATUS_BLUE,
            "black": STATUS_BLACK
        }
        indicator = status_map.get(color.lower(), STATUS_BLACK)
        self.root.after(0, lambda: self.status_label.configure(text=f"{indicator} {status_text}"))

def main():
    load_dotenv()
    
    # Create the custom tkinter window
    root = ctk.CTk()
    
    # Set window attributes for a more modern look
    root.title("Meeting Assistant")
    
    # Make window dragable without title bar (optional)
    # root.overrideredirect(True)
    
    # Keep on top of other windows like Zoom
    root.attributes("-topmost", True)
    
    # Create the app
    app = MeetingAssistantApp(root)
    
    root.mainloop()

if __name__ == "__main__":
    main()