# Voice Assistant Speech-to-Speech Demo

A full-stack sample that streams microphone audio from a Next.js frontend into Azure Voice Live through a FastAPI backend and returns real-time synthesized speech. The implementation keeps the developer ergonomics of the original sample while wiring the app to the official `azure-ai-voicelive` SDK for bi-directional speech and function-calling support.

## Project layout

```
.
├── backend/        # FastAPI application with REST + WebSocket endpoints
├── frontend/       # Next.js (App Router) UI with ShadCN-inspired components
├── async_function_calling_sample.py  # Original reference script from Azure sample
└── requirements.txt  # Legacy dependencies from the original sample
```

## Features

- **Live speech-to-speech loop** – microphone audio is downsampled to PCM16, streamed to Azure Voice Live, and playback switches to real-time TTS responses as they arrive.
- **Conversation memory** – user, assistant, and system messages are rendered with rolling transcripts from the Azure service.
- **Function calling ready** – the backend ships with helper scaffolding so you can add functions invoked by Azure Voice Live.
- **Fallback REST endpoint** – `/interaction` still exists for simple text-based checks while iterating offline.
- **Docker ready** – separate Dockerfiles for backend and frontend for containerised development.

## Prerequisites

- Node.js 20+ (the Dockerfile uses Node 22)
- Python 3.11 or 3.12 (Dockerfile uses Python 3.12)
- An Azure subscription with access to **Azure Voice Live** (preview) and an API key or federated identity that works with `DefaultAzureCredential`
- `npm` and `python` available locally if you prefer running without containers

## Backend setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Environment variables:

- `FRONTEND_ORIGIN` – comma-separated list of origins allowed by CORS (default: `http://localhost:3000`).
- `AZURE_VOICELIVE_API_KEY` – API key for the Azure Voice Live endpoint. If omitted, the backend falls back to `DefaultAzureCredential` (managed identity, Azure CLI sign-in, etc.).
- `AZURE_VOICELIVE_ENDPOINT` – WebSocket endpoint for Voice Live (default: `wss://api.voicelive.com/v1`).
- `AZURE_VOICELIVE_MODEL` – Voice Live model deployment name (default: `gpt-4o-realtime-preview`).
- `AZURE_VOICELIVE_VOICE` – Speech synthesis voice (default: `en-US-AvaNeural`).
- `AZURE_VOICELIVE_INSTRUCTIONS` – Optional system prompt that configures the assistant persona.
- `AZURE_VOICELIVE_SHOW_TRANSCRIPTIONS` – Set to `false` to disable interim transcript events.

### Backend via Docker

```bash
cd backend
docker build -t voice-assistant-backend .
docker run -p 8000:8000 --env FRONTEND_ORIGIN=http://localhost:3000 voice-assistant-backend
```

## Frontend setup

```bash
cd frontend
npm install
npm run dev
```

The app uses two environment variables (optional in development):

- `NEXT_PUBLIC_BACKEND_HTTP` – HTTP base URL for REST calls (default: `http://localhost:8000`).
- `NEXT_PUBLIC_BACKEND_WS` – WebSocket URL (default: `ws://localhost:8000/ws`).

### Frontend via Docker

```bash
cd frontend
docker build -t voice-assistant-frontend .
docker run -p 3000:3000 --env NEXT_PUBLIC_BACKEND_HTTP=http://host.docker.internal:8000 --env NEXT_PUBLIC_BACKEND_WS=ws://host.docker.internal:8000/ws voice-assistant-frontend
```

## Development notes

- The backend uses the official `azure-ai-voicelive` SDK over WebSockets. Provide either `AZURE_VOICELIVE_API_KEY` or ensure `DefaultAzureCredential` can acquire tokens (Azure CLI login, managed identity, etc.).
- Input audio is captured with an `AudioWorkletProcessor`, resampled to 24 kHz PCM16, and flushed to the backend in ~200 ms frames.
- Playback leverages the Web Audio API to enqueue PCM16 buffers as soon as they land, so you hear the response while it is still being generated.
- ShadCN styling conventions are reproduced with Tailwind CSS utilities and a shared button component.

## Testing

- Python modules compile cleanly: `python -m compileall backend`
- Frontend production build passes: `npm run build`

Feel free to replace the mock `MockAssistant` with Azure Voice Live SDK calls once your credentials and runtime are ready.
