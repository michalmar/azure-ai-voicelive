# Developer Guide

## Project Overview

This is a full-stack voice assistant application with:
- **Backend**: FastAPI with WebSocket support for real-time audio streaming
- **Frontend**: Next.js with TypeScript, Tailwind CSS, and Shadcn UI
- **Communication**: WebSocket-based bidirectional audio streaming (PCM16, 24kHz)

## Development Setup

### Quick Start

Run the setup script:
```bash
./setup.sh
```

### Manual Setup

#### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Add your AZURE_VOICELIVE_API_KEY to .env
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend
```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

## Architecture Details

### WebSocket Protocol

The application uses a custom WebSocket protocol for real-time communication:

#### Client to Server
- `audio`: PCM16 audio data (base64 encoded)
- `stop_audio`: Signal that user stopped speaking

#### Server to Client
- `ready`: Session initialized
- `user_started_speaking`: Voice activity detected
- `user_stopped_speaking`: Silence detected
- `assistant_response_started`: Assistant is responding
- `audio`: PCM16 audio data (base64 encoded)
- `assistant_response_ended`: Assistant finished speaking
- `user_transcript`: What the user said
- `assistant_transcript`: What the assistant said
- `function_call`: Function being called
- `error`: Error message

### Audio Processing

**Format**: PCM16, 24kHz, Mono

**Client (Browser)**:
1. Capture audio using Web Audio API
2. Convert Float32 to PCM16
3. Encode to base64
4. Send via WebSocket

**Server (Backend)**:
1. Receive base64 audio
2. Forward to Azure VoiceLive SDK
3. Receive TTS audio from Azure
4. Encode to base64
5. Send back to client

**Client (Browser)**:
1. Receive base64 audio
2. Decode to PCM16
3. Convert to Float32
4. Queue for playback
5. Play using Web Audio API

### Function Calling

The assistant can call functions defined in `backend/app/main.py`:

```python
AVAILABLE_FUNCTIONS = {
    "get_current_time": get_current_time,
    "get_current_weather": get_current_weather,
}
```

To add a new function:

1. Define the function:
```python
def my_function(arguments: Union[str, Mapping[str, Any]]) -> Dict[str, Any]:
    # Parse arguments
    if isinstance(arguments, str):
        args = json.loads(arguments)
    else:
        args = arguments
    
    # Your logic here
    return {"result": "value"}
```

2. Add to AVAILABLE_FUNCTIONS:
```python
AVAILABLE_FUNCTIONS["my_function"] = my_function
```

3. Add to function_tools in setup_session:
```python
FunctionTool(
    name="my_function",
    description="Description of what the function does",
    parameters={
        "type": "object",
        "properties": {
            "param_name": {
                "type": "string",
                "description": "Parameter description"
            }
        },
        "required": ["param_name"]
    }
)
```

## Frontend Customization

### Changing Assistant Icon

Edit `frontend/app/page.tsx`:
```typescript
import { YourIcon } from "lucide-react";

// Replace Volume2 with YourIcon
<YourIcon className="w-48 h-48 text-purple-400" />
```

### Adding New Animations

Add to `frontend/app/globals.css`:
```css
@keyframes your-animation {
  0% { /* start state */ }
  100% { /* end state */ }
}

.animate-your-animation {
  animation: your-animation 2s ease-in-out infinite;
}
```

### Changing Colors

Edit the color scheme in `frontend/app/globals.css` using the CSS variables.

## Backend Customization

### Changing Voice

Edit `backend/app/main.py` in the `setup_session` function:
```python
voice_config = AzureStandardVoice(name="en-US-JennyNeural")
# See Azure docs for available voices
```

### Adjusting Voice Detection

Edit the `ServerVad` configuration:
```python
turn_detection_config = ServerVad(
    threshold=0.5,              # Sensitivity (0.0-1.0)
    prefix_padding_ms=300,      # Audio before speech
    silence_duration_ms=500     # Silence before stopping
)
```

### Adding Custom Instructions

Edit the instructions in `setup_session`:
```python
instructions=(
    "You are a helpful AI assistant with a specific personality. "
    "Your custom instructions here..."
)
```

## Testing

### Test Backend Locally
```bash
cd backend
python -m pytest  # If you add tests
```

### Test WebSocket Connection
```bash
# Using websocat (install: brew install websocat)
websocat ws://localhost:8000/ws/voice
```

### Check API Docs
Open `http://localhost:8000/docs` for interactive API documentation.

## Deployment

### Docker Deployment
```bash
docker-compose up --build
```

### Production Considerations

1. **Environment Variables**: Use proper secrets management
2. **CORS**: Restrict to your domain in production
3. **HTTPS/WSS**: Use secure protocols
4. **Rate Limiting**: Add rate limiting to prevent abuse
5. **Logging**: Configure proper logging and monitoring
6. **Error Handling**: Add comprehensive error handling

## Configuration Options

### Backend Environment Variables

| Variable | Description | Default | Values |
|----------|-------------|---------|--------|
| `AZURE_VOICELIVE_API_KEY` | Azure API key for Voice Live service | (required) | Your API key |
| `AZURE_VOICELIVE_ENDPOINT` | WebSocket endpoint URL | (required) | `wss://api.voicelive.com/v1` |
| `AZURE_VOICELIVE_MODEL` | Model identifier | (required) | `gpt-4o-realtime-preview` |
| `AZURE_VOICELIVE_SHOW_TRANSCRIPTIONS` | Control transcription display | `True` | `True` or `False` |

#### AZURE_VOICELIVE_SHOW_TRANSCRIPTIONS

This environment variable controls whether transcriptions are sent from the backend to the frontend:

- **`True` (default)**: Both user and assistant transcriptions are sent via WebSocket and displayed in the UI
  - Shows what you said in real-time
  - Shows what the assistant is saying
  - Useful for debugging and accessibility

- **`False`**: No transcription messages are sent
  - Reduces WebSocket traffic
  - Provides a cleaner, audio-only experience
  - UI only shows the animated audio visualization orb

**Example:**
```bash
# In backend/.env
AZURE_VOICELIVE_SHOW_TRANSCRIPTIONS=False  # Hide transcriptions
```

### Deploy to Azure

1. **Azure Container Apps**:
```bash
az containerapp up --name voice-assistant --resource-group myRG --source .
```

2. **Azure Web App**:
```bash
az webapp up --name voice-assistant --runtime "PYTHON:3.11"
```

## Common Issues

### Port Already in Use
```bash
# Find process using port
lsof -ti:8000 | xargs kill -9  # Backend
lsof -ti:3000 | xargs kill -9  # Frontend
```

### WebSocket Connection Refused
- Check backend is running
- Verify NEXT_PUBLIC_WS_URL is correct
- Check firewall settings

### No Audio Input
- Grant microphone permissions
- Check browser console for errors
- Try HTTPS (some browsers require secure context)

### Function Calls Not Working
- Verify API key permissions
- Check backend logs
- Ensure function definitions match schema

## Performance Tips

1. **Audio Buffer Size**: Adjust `chunk_size` in audio processing
2. **Queue Management**: Tune audio queue handling
3. **WebSocket Reconnection**: Add automatic reconnection logic
4. **Error Recovery**: Implement graceful degradation

## Code Style

- **Backend**: Follow PEP 8
- **Frontend**: Use Prettier and ESLint
- **TypeScript**: Enable strict mode

## Useful Commands

```bash
# Backend
cd backend
python -m uvicorn app.main:app --reload  # Development
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app  # Production

# Frontend
cd frontend
npm run dev      # Development
npm run build    # Production build
npm run start    # Production server
npm run lint     # Check code style

# Docker
docker-compose up         # Start services
docker-compose down       # Stop services
docker-compose logs -f    # View logs
```

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [Azure AI Voice Live](https://learn.microsoft.com/azure/)
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)
- [Shadcn UI](https://ui.shadcn.com/)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review existing issues
3. Create a new issue with detailed information
