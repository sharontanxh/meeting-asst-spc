import os
import threading
import tkinter as tk
from tkinter import filedialog

from dotenv import load_dotenv

from agent_flow import AgentManager
from transcription import ElevenLabsTranscriptionManager


class MeetingAssistantApp:
    def __init__(self, root):
        # Initialize the main window
        self.root = root
        self.root.title("Meeting Assistant")
        self.root.geometry("400x350")  # Increased height for debug button

        # Global state
        self.meeting_transcript = ""

        # Initialize managers
        self.transcription_manager = ElevenLabsTranscriptionManager(
            callback_new_text=self.on_new_transcript
        )
        self.agent_manager = AgentManager(callback_status_update=self.update_status)

        # Set up UI
        self.setup_ui()

    def setup_ui(self):
        # Status display
        status_frame = tk.Frame(self.root)
        status_frame.pack(pady=10)

        self.status_label = tk.Label(
            status_frame, text="Not Transcribing", fg="red", font=("Arial", 12)
        )
        self.status_label.pack()

        # Create buttons
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=20)

        self.transcription_button = tk.Button(
            button_frame, text="Start Transcribing", command=self.toggle_transcription
        )
        self.transcription_button.grid(row=0, column=0, padx=10)

        self.agent_button = tk.Button(
            button_frame, text="Activate Agent", command=self.activate_agent
        )
        self.agent_button.grid(row=0, column=1, padx=10)

        self.resume_button = tk.Button(
            button_frame, text="Resume Transcription", command=self.resume_transcription
        )
        self.resume_button.grid(row=0, column=2, padx=10)

        # Debug button section
        debug_frame = tk.Frame(self.root)
        debug_frame.pack(pady=10)

        debug_label = tk.Label(
            debug_frame, text="Debug Options:", font=("Arial", 10, "bold")
        )
        debug_label.pack(pady=5)

        self.load_transcript_button = tk.Button(
            debug_frame,
            text="Load Debug Transcript",
            command=self.load_debug_transcript,
            bg="#f0f0f0",
        )
        self.load_transcript_button.pack(pady=5)

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
        print(
            f"[Callback Main] on_new_transcript received text (length {len(new_text)}): '{new_text[:100]}...'"
        )  # Log callback received
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

        # --- Debug: Print transcript before passing to agent ---
        print(
            f"Activating agent with transcript (length {len(self.meeting_transcript)}):"
        )
        print(
            f"'{self.meeting_transcript[:500]}{'...' if len(self.meeting_transcript) > 500 else ''}'"
        )
        # --- End Debug ---

        # Run agent in a separate thread
        agent_thread = threading.Thread(
            target=lambda: self.agent_manager.run_agent(self.meeting_transcript)
        )
        agent_thread.daemon = True
        agent_thread.start()

    def load_debug_transcript(self):
        """Load a transcript from a file for debugging and feed it to the agent"""
        # Default file path
        file_path = "transcript.txt"

        # Check if the default file exists
        if not os.path.exists(file_path):
            # If not, open a file dialog
            file_path = filedialog.askopenfilename(
                title="Select Transcript File",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            )

            # If user cancels the dialog
            if not file_path:
                self.update_status("Debug: No file selected", "red")
                return

        # Update status
        self.update_status("Loading debug transcript...", "blue")

        # Load the transcript in a separate thread
        def load_and_run():
            # Load transcript from file
            transcript = self.agent_manager.load_transcript_from_file(file_path)

            if transcript:
                # Store in app state
                self.meeting_transcript = transcript

                # Run the agent
                self.update_status("Running agent with debug transcript...", "blue")
                self.agent_manager.run_agent(transcript)
            else:
                self.update_status("Failed to load transcript", "red")

        # Start the thread
        debug_thread = threading.Thread(target=load_and_run)
        debug_thread.daemon = True
        debug_thread.start()

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
