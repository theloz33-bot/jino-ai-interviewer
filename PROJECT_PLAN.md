# AI Interviewer Project Plan (DRAFT)

## 1. Project Overview
- **Goal:** Create a real-time AI interview practice tool.
- **Key Features:**
    - Real-time Speech-to-Text (STT) for user answers.
    - AI Logic (LLM) for generating context-aware follow-up questions.
    - Text-to-Speech (TTS) for the interviewer's voice.
    - Post-interview evaluation (Logic, Clarity, Keyword usage).

## 2. Technical Stack
- **Language:** Python 3.10+
- **Core Framework:** `FastAPI` (Backend) + `Streamlit` or `React` (Frontend - simple UI for now).
- **AI Models:**
    - **LLM (Brain):** OpenAI GPT-4o (or Gemini Pro) via API.
        - Role: Analyzes answers, generates follow-up questions, evaluates performance.
    - **STT (Ears):** OpenAI Whisper (API or Local model for lower latency).
    - **TTS (Mouth):** ElevenLabs (High quality) or OpenAI TTS (Fast).

## 3. Architecture
1. **User speaks** -> Microphone -> Audio Stream.
2. **STT** converts Audio to Text.
3. **LLM** receives Text + Conversation History.
4. **LLM** generates:
    - Assessment of the answer.
    - Next Question.
5. **TTS** converts Next Question to Audio.
6. **User hears** the question.

## 4. Evaluation Metrics (Prompt Engineering)
The AI will score answers based on:
- **Logical Flow (0-10):** Structured reasoning (STAR method).
- **Relevance (0-10):** Did it answer the specific question?
- **Keywords:** Usage of industry-standard terms.
- **Attitude/Tone:** Professionalism and confidence.

## 5. Directory Structure
```
D:\Projects\jino-ai-interviewer\
├── main.py              # Entry point
├── requirements.txt     # Dependencies
├── .env                 # API Keys
├── modules\
│   ├── audio_recorder.py # Mic input handling
│   ├── transcriber.py    # STT (Whisper)
│   ├── interviewer.py    # LLM Logic (GPT)
│   └── speaker.py        # TTS (ElevenLabs/OpenAI)
└── logs\                 # Interview transcripts
```
