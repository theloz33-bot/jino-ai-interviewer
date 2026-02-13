# AI Interviewer (Jino's Project)

## Overview
A real-time AI interview practice tool. This agent will act as a strict but constructive interviewer.
It uses **OpenAI GPT-4o** for logic, **Whisper** for hearing (STT), and **ElevenLabs** for speaking (TTS).

## Getting Started

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   *Note: PyAudio might need `pip install pipwin` & `pipwin install pyaudio` on Windows if direct install fails.*

2. **Set API Keys (.env):**
   Create a `.env` file and add your keys:
   ```env
   OPENAI_API_KEY=sk-...
   ELEVENLABS_API_KEY=xi-...
   ```

3. **Run the Interviewer:**
   (Script to be implemented in `main.py`)
   ```bash
   python main.py
   ```

## Structure
- `modules/`: Contains core logic (STT, TTS, LLM).
- `logs/`: Saves interview transcripts for review.
