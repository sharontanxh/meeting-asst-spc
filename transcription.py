import requests
import json
import os
import threading
import time
import pyaudio
import wave
from io import BytesIO
from datetime import datetime

class ElevenLabsTranscriptionManager:
    def __init__(self, callback_new_text=None):
        self.is_transcribing = False
        self.callback_new_text = callback_new_text
        self.api_key = os.environ.get("ELEVENLABS_API_KEY", "")
        
        # Define transcript directory and create if it doesn't exist
        self.transcript_dir = "data/transcripts"
        os.makedirs(self.transcript_dir, exist_ok=True)
        
        # Generate timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.transcript_file = os.path.join(self.transcript_dir, f"meeting_transcript_{timestamp}.txt")
        
        # Audio settings for capturing
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.chunk = 1024 * 4
        self.recording_seconds = 10  # Process in 10-second chunks
        self.audio = None
        self.stream = None
        
        # Create or clear the transcript file (now using the timestamped path)
        with open(self.transcript_file, "w") as f:
            f.write("")
    
    def start_transcription(self):
        """Start the transcription process"""
        if not self.is_transcribing:
            self.is_transcribing = True
            
            # Initialize PyAudio
            self.audio = pyaudio.PyAudio()
            self.stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk
            )
            
            # Start a new thread for transcription
            self.transcription_thread = threading.Thread(target=self._transcription_loop)
            self.transcription_thread.daemon = True
            self.transcription_thread.start()
    
    def stop_transcription(self):
        """Stop the transcription process"""
        self.is_transcribing = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.audio:
            self.audio.terminate()
        self.stream = None
        self.audio = None
    
    def _transcription_loop(self):
        """Main transcription processing loop"""
        while self.is_transcribing:
            try:
                # Record audio for a set duration
                frames = []
                for i in range(0, int(self.rate / self.chunk * self.recording_seconds)):
                    if not self.is_transcribing:
                        break
                    data = self.stream.read(self.chunk, exception_on_overflow=False)
                    frames.append(data)
                
                if not frames or not self.is_transcribing:
                    continue
                
                # Convert to WAV format
                audio_data = BytesIO()
                with wave.open(audio_data, 'wb') as wf:
                    wf.setnchannels(self.channels)
                    wf.setsampwidth(self.audio.get_sample_size(self.format))
                    wf.setframerate(self.rate)
                    wf.writeframes(b''.join(frames))
                
                audio_data.seek(0)
                
                # Send to ElevenLabs API
                transcript = self._transcribe_with_elevenlabs(audio_data)
                
                # Process and save the transcript
                if transcript:
                    formatted_text = self._format_transcript(transcript)
                    
                    # Save to file
                    with open(self.transcript_file, "a") as f:
                        f.write(formatted_text)
                    
                    # Notify via callback
                    if self.callback_new_text:
                        self.callback_new_text(formatted_text)
                
            except Exception as e:
                print(f"Transcription error: {e}")
            
            # Short delay to prevent CPU overuse
            time.sleep(0.1)
    
    def _transcribe_with_elevenlabs(self, audio_data):
        """Send audio to ElevenLabs API for transcription"""
        if not self.api_key:
            print("[ElevenLabs STT API] Error: API key is missing!")
            return None
            
        try:
            # ElevenLabs API endpoint
            url = "https://api.elevenlabs.io/v1/speech-to-text"
            
            headers = {
                "xi-api-key": self.api_key
            }
            
            files = {
                "file": ("audio.wav", audio_data, "audio/wav")
            }
            
            # Re-add the data dictionary with the required model_id
            data = {
                "model_id": "scribe_v1", # Use the correct STT model ID
                # Add other parameters if needed, e.g., language_code
                # "language_code": "en"
            }
            
            response = requests.post(url, headers=headers, files=files, data=data)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"[ElevenLabs STT API] Error ({response.status_code}): {response.text}")
                return None
                
        except Exception as e:
            print(f"[ElevenLabs STT API] Error sending request: {e}")
            return None
    
    def _format_transcript(self, transcript_json):
        """Extract and format the transcript text from API response"""
        try:
            # Handle potential structure from speech-to-text API
            # Adjust based on actual API response structure
            if isinstance(transcript_json, dict) and "results" in transcript_json:
                 # Example: Processing a hypothetical structure
                 full_text = "".join([res.get("transcript", "") for res in transcript_json["results"]])
                 return full_text + " "
            elif isinstance(transcript_json, dict) and "text" in transcript_json: # Check existing simple case
                return transcript_json["text"] + " "
            else:
                 # Attempting to handle raw text response if JSON parsing failed or structure unknown
                 if isinstance(transcript_json, str):
                     return transcript_json + " "
                 return "Transcription response format not recognized. "
            
        except Exception as e:
            print(f"Error formatting transcript: {e}")
            return "Error formatting transcript. "