# Quick Reference Card

## 🚀 Quick Start

### Option 1: Docker (Recommended)
```bash
# 1. Configure
cp .env.example .env
# Edit .env and add AZURE_VOICELIVE_API_KEY

# 2. Run
docker-compose up --build

# 3. Access
# http://localhost:3000
```

### Option 2: Local Development
```bash
# 1. Run setup
./setup.sh

# 2. Terminal 1 - Backend
cd backend && source venv/bin/activate
python -m uvicorn app.main:app --reload

# 3. Terminal 2 - Frontend
cd frontend && npm run dev

# 4. Access
# http://localhost:3000
```

## 📁 Project Structure

```
azure-ai-voicelive/
├── backend/              # FastAPI backend
│   ├── app/main.py      # Main application
│   ├── requirements.txt # Python dependencies
│   └── Dockerfile       # Backend container
├── frontend/            # Next.js frontend
│   ├── app/page.tsx    # Main UI
│   ├── package.json    # Node dependencies
│   └── Dockerfile      # Frontend container
└── docker-compose.yml  # Orchestration
```

## 🔑 Environment Variables

**Backend (.env)**
```env
AZURE_VOICELIVE_API_KEY=your_key_here
AZURE_VOICELIVE_ENDPOINT=wss://api.voicelive.com/v1
```

**Frontend (.env.local)**
```env
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/voice
```

## 🎨 UI States

| State | Color | Meaning |
|-------|-------|---------|
| 💜 Idle | Purple | Ready for input |
| 🔵 Listening | Blue | Capturing speech |
| 🟡 Processing | Yellow | AI thinking |
| 🟢 Speaking | Green | AI responding |

## 📡 API Endpoints

- `GET /` - Health check
- `GET /health` - Health status
- `GET /docs` - API documentation
- `WS /ws/voice` - Voice WebSocket

## 🔧 Common Commands

### Backend
```bash
cd backend
source venv/bin/activate              # Activate venv
pip install -r requirements.txt       # Install deps
python -m uvicorn app.main:app --reload  # Run dev
```

### Frontend
```bash
cd frontend
npm install                   # Install deps
npm run dev                   # Development
npm run build                 # Build for production
npm run start                 # Run production
npm run lint                  # Lint code
```

### Docker
```bash
docker-compose up             # Start services
docker-compose up -d          # Start detached
docker-compose down           # Stop services
docker-compose logs -f        # View logs
docker-compose ps             # List services
```

## 🎯 Test Commands

Try saying:
- "What's the current time?"
- "What time is it in UTC?"
- "What's the weather in Seattle?"
- "Tell me the weather in New York"

## 🐛 Troubleshooting

### Microphone Access
- Check browser permissions
- Use HTTPS for production
- Reload page after granting access

### WebSocket Connection Failed
- Verify backend is running: `http://localhost:8000/health`
- Check NEXT_PUBLIC_WS_URL in frontend/.env.local
- Review browser console for errors

### No Audio Playback
- Check system audio settings
- Test speakers/headphones
- Review browser audio permissions

### Docker Issues
```bash
# Rebuild containers
docker-compose build --no-cache

# Clean up
docker-compose down -v
docker system prune -a
```

## 📚 Documentation Files

- `PROJECT_README.md` - Complete documentation
- `DEVELOPER_GUIDE.md` - Development guide
- `PROJECT_SUMMARY.md` - Project overview
- `setup.sh` - Automated setup script

## 🌐 URLs

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## 🔐 Security Checklist

- [ ] Add AZURE_VOICELIVE_API_KEY to .env
- [ ] Never commit .env files
- [ ] Use HTTPS in production
- [ ] Restrict CORS in production
- [ ] Use environment-specific configs

## 📞 Support

- Backend Issues: Check `backend/app/main.py`
- Frontend Issues: Check `frontend/app/page.tsx`
- WebSocket: Check browser console & backend logs
- Audio: Check Web Audio API compatibility

---

**Need more help?**
- See PROJECT_README.md for full documentation
- See DEVELOPER_GUIDE.md for development details
- Check backend logs for detailed error messages
