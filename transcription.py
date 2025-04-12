import time
import threading
import os

class TranscriptionManager:
    """Manages audio capture and transcription"""
    
    def __init__(self, callback_new_text=None):
        self.is_transcribing = False
        self.transcription_thread = None
        self.callback_new_text = callback_new_text
        self.transcript_file = "meeting_transcript.txt"
        
        # Create or clear the transcript file
        with open(self.transcript_file, "w") as f:
            f.write("")
    
    def start_transcription(self):
        """Start the transcription process"""
        if not self.is_transcribing:
            self.is_transcribing = True
            
            # Start a new thread if needed
            if self.transcription_thread is None or not self.transcription_thread.is_alive():
                self.transcription_thread = threading.Thread(target=self._transcription_loop)
                self.transcription_thread.daemon = True
                self.transcription_thread.start()
    
    def stop_transcription(self):
        """Stop the transcription process"""
        self.is_transcribing = False
    
    def _transcription_loop(self):
        """Main transcription processing loop"""
        while self.is_transcribing:
            try:
                # In a real implementation, you would:
                # 1. Capture audio from the microphone
                # 2. Process it through a transcription service
                
                # For the hackathon, simulate with a simple delay
                time.sleep(1)
                new_text = self._transcribe_audio_chunk()
                
                # Save to file
                with open(self.transcript_file, "a") as f:
                    f.write(new_text)
                
                # Notify via callback
                if self.callback_new_text:
                    self.callback_new_text(new_text)
                    
            except Exception as e:
                print(f"Transcription error: {e}")
            
            # Short delay to prevent CPU overuse
            time.sleep(0.1)
    
    def _transcribe_audio_chunk(self):
        """Transcribe an audio chunk to text"""
        # In a real implementation, you would use a transcription service
        # For the hackathon, generate simulated text
        simulated_texts = [
            "We need to finish the agent implementation by tomorrow. ",
            "Let's schedule a follow-up meeting next week. ",
            "The transcription accuracy needs improvement. ",
            "We should add more tools to the agent. ",
            "How do we integrate with the vector database? "
        ]
        import random
        return random.choice(simulated_texts)