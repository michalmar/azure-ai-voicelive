# Azure AI Voice Live Assistant

A full-stack web application demonstrating real-time speech-to-speech interaction with a personal AI assistant using Azure AI Voice Live SDK.

![Voice Assistant](https://img.shields.io/badge/Azure-AI%20Voice%20Live-blue)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-green)
![Next.js](https://img.shields.io/badge/Frontend-Next.js-black)

## ✨ Features

- **Real-time Speech-to-Speech Communication**: Talk naturally with the AI assistant
- **WebSocket Connection**: Low-latency bidirectional audio streaming
- **Function Calling**: Assistant can call functions to get real-time information (weather, time, etc.)
- **Beautiful UI**: Animated assistant orb with different states:
  - 💜 **Idle**: Subtle pulsing glow
  - 🔵 **Listening**: Blue pulsing animation when you speak
  - 🟡 **Processing**: Yellow spinning animation while thinking
  - 🟢 **Speaking**: Green glowing and spinning when assistant responds
- **Microphone Mute**: Toggle microphone on/off during conversation
- **Live Transcriptions**: See what you and the assistant are saying in real-time
- **Responsive Design**: Works on desktop and mobile devices

## 🏗️ Architecture

```
┌─────────────────┐         WebSocket          ┌─────────────────┐
│                 │◄──────────────────────────►│                 │
│  Next.js        │   Audio Streaming          │  FastAPI        │
│  Frontend       │   (PCM16, 24kHz)          │  Backend        │
│  (TypeScript)   │                            │  (Python)       │
│                 │                            │                 │
└────────┬────────┘                            └────────┬────────┘
         │                                              │
         │ Web Audio API                               │
         │ - Microphone capture                        │
         │ - Audio playback                            │
         │                                              │
         └──────────────────────────────────────────────┘
                     Azure AI Voice Live SDK
                     - Speech recognition
                     - Function calling
                     - Text-to-speech
```

## 📁 Project Structure

```
azure-ai-voicelive/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── __init__.py
│   │   └── main.py            # Main FastAPI application with WebSocket
│   ├── Dockerfile             # Backend container
│   ├── requirements.txt       # Python dependencies
│   └── .env.example          # Environment variables template
│
├── frontend/                  # Next.js frontend
│   ├── app/
│   │   ├── globals.css       # Global styles with animations
│   │   ├── layout.tsx        # Root layout
│   │   └── page.tsx          # Main page with voice assistant UI
│   ├── components/
│   │   └── ui/               # Shadcn UI components
│   ├── lib/
│   │   └── utils.ts          # Utility functions
│   ├── Dockerfile            # Frontend container
│   ├── package.json          # Node.js dependencies
│   └── .env.example          # Environment variables template
│
├── docker-compose.yml         # Docker orchestration
└── README.md                 # This file
```

## 🚀 Getting Started

### Prerequisites

- **Node.js** 20.x or higher
- **Python** 3.11 or higher
- **Docker** (optional, for containerized deployment)
- **Azure VoiceLive API Key** (get from Azure Portal)
- **Microphone** access for voice input

### Option 1: Local Development

#### 1. Clone the Repository

```bash
git clone <repository-url>
cd azure-ai-voicelive
```

#### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env and add your Azure VoiceLive API key

# Run the backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend will be available at `http://localhost:8000`

#### 3. Frontend Setup

Open a new terminal:

```bash
cd frontend

# Install dependencies
npm install

# Configure environment variables
cp .env.example .env.local
# Edit .env.local if needed (default WS URL is ws://localhost:8000/ws/voice)

# Run the frontend
npm run dev
```

The frontend will be available at `http://localhost:3000`

#### 4. Open Your Browser

Navigate to `http://localhost:3000` and grant microphone permissions when prompted.

### Option 2: Docker Deployment

#### 1. Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your Azure VoiceLive API key
nano .env
```

#### 2. Build and Run with Docker Compose

```bash
# Build and start all services
docker-compose up --build

# Or run in detached mode
docker-compose up -d --build
```

#### 3. Access the Application

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`

#### 4. Stop Services

```bash
docker-compose down
```

## 🔧 Configuration

### Backend Environment Variables

Create a `.env` file in the `backend/` directory:

```env
AZURE_VOICELIVE_API_KEY=your_api_key_here
AZURE_VOICELIVE_ENDPOINT=wss://api.voicelive.com/v1
```

### Frontend Environment Variables

Create a `.env.local` file in the `frontend/` directory:

```env
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/voice
```

For production, update the WebSocket URL to your deployed backend URL.

## 🎯 Usage

1. **Start Conversation**: Click the "Start Conversation" button
2. **Grant Permissions**: Allow microphone access when prompted
3. **Start Speaking**: The assistant will automatically detect when you start speaking
4. **Listen to Response**: The assistant's response will play automatically
5. **Mute/Unmute**: Use the microphone button to mute/unmute during conversation
6. **Stop**: Click "Stop Conversation" to end the session

### Try These Commands

- "What's the current time?"
- "What time is it in UTC?"
- "What's the weather in Seattle?"
- "Tell me the weather in San Francisco"

## 🎨 UI States

The assistant orb changes appearance based on its state:

| State | Color | Animation | Description |
|-------|-------|-----------|-------------|
| **Idle** | 💜 Purple | Subtle pulse | Ready for input |
| **Listening** | 🔵 Blue | Fast pulse + ping | Listening to you speak |
| **Processing** | 🟡 Yellow | Slow spin + pulse | Thinking about response |
| **Speaking** | 🟢 Green | Glow + spin | Speaking response |

## 🛠️ Technology Stack

### Backend
- **FastAPI**: Modern, fast web framework for Python
- **Azure AI Voice Live SDK**: Real-time voice conversation
- **WebSockets**: Bidirectional communication
- **Uvicorn**: ASGI server

### Frontend
- **Next.js 15**: React framework with App Router
- **TypeScript**: Type-safe JavaScript
- **Tailwind CSS v4**: Utility-first CSS framework
- **Shadcn UI**: Beautiful, accessible components
- **Lucide React**: Icon library
- **Web Audio API**: Audio capture and playback

## 📡 API Endpoints

### WebSocket Endpoint

**`/ws/voice`**

Establishes a WebSocket connection for real-time voice interaction.

#### Client → Server Messages

```typescript
// Send audio data
{
  "type": "audio",
  "data": "base64_encoded_pcm16_audio"
}

// Stop audio signal
{
  "type": "stop_audio"
}
```

#### Server → Client Messages

```typescript
// Session ready
{ "type": "ready", "message": "Voice assistant ready" }

// User started speaking
{ "type": "user_started_speaking" }

// User stopped speaking
{ "type": "user_stopped_speaking" }

// Assistant response started
{ "type": "assistant_response_started" }

// Audio data
{ "type": "audio", "data": "base64_encoded_pcm16_audio" }

// User transcript
{ "type": "user_transcript", "text": "..." }

// Assistant transcript
{ "type": "assistant_transcript", "text": "..." }

// Function call
{ "type": "function_call", "function": "function_name" }

// Error
{ "type": "error", "message": "error_description" }
```

### HTTP Endpoints

**`GET /`** - Health check

**`GET /health`** - Health status

**`GET /docs`** - Interactive API documentation (Swagger UI)

## 🔒 Security Considerations

- **API Keys**: Never commit API keys to version control
- **CORS**: Configure CORS properly for production (currently set to `*` for development)
- **Environment Variables**: Use proper environment variable management
- **HTTPS**: Use HTTPS/WSS in production for secure communication

## 🐛 Troubleshooting

### Microphone Access Issues

- Ensure browser has microphone permissions
- Check system microphone settings
- Try using HTTPS (some browsers require secure context)

### WebSocket Connection Failed

- Verify backend is running on correct port
- Check `NEXT_PUBLIC_WS_URL` in frontend `.env.local`
- Ensure firewall allows WebSocket connections

### No Audio Playback

- Check browser audio permissions
- Verify speakers/headphones are connected
- Test with different audio output device

### Function Calling Not Working

- Verify Azure VoiceLive API key has necessary permissions
- Check backend logs for function execution errors

## 📝 License

This project is licensed under the MIT License.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📧 Support

For issues related to:
- **Azure AI Voice Live SDK**: Check [Azure documentation](https://learn.microsoft.com/azure/)
- **This application**: Open an issue in the repository

## 🙏 Acknowledgments

- Azure AI Voice Live team for the excellent SDK
- Shadcn for the beautiful UI components
- FastAPI and Next.js communities

---

**Built with ❤️ using Azure AI Voice Live SDK**
