# Getting started
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
brew install portaudio # to use device audio
brew install python-tk@3.13 # for tkinter local version
brew instal ffmpeg # for speech generation, elevenlabs' play() function
```
Create and populate a .env file with the necessary IDs/Keys

# TODOs
- Agent Flow: extend from single-step tool use to multi-step tool use (while loop with some guard-rails)
- Front end: update from text labels to more intuitive buttons -> also a bit buggy now, you can transcribe while the agent is speaking
- All The Tools
- Integrate the tools with the flow
- Testability - have each part pass on a fake 'flow' to the next one so that we can specify debug paths and isolate the section we want to test.
- Active listening (wake up mode instead of button)