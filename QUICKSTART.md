# Quick Start

1. Double-click LAUNCH_BOT.bat to run locally.
2. For deployment, see deployment documentation or ask for help.
### Run the Project

**Terminal 1 - Backend API (Already Running)**
```bash
cd "C:\Users\Shubh\OneDrive\Desktop\MindDoc AI"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
# MindDoc AI - Complete Project Setup

**Status**: ✓ COMPLETE AND FULLY OPERATIONAL

## Quick Start

### Prerequisites
Python 3.11+
Node.js & npm

**No Ollama install required!**
All AI models and the llama.cpp server are bundled and auto-downloaded by the installer. The app will auto-update models and server as needed. Just install and run—no extra steps.
- Python 3.11+
- Node.js & npm

### Run the Project

**Terminal 1 - Backend API (Already Running)**
```bash
cd "C:\Users\Shubh\OneDrive\Desktop\MindDoc AI"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Expected: `Uvicorn running on http://127.0.0.1:8000`

**Terminal 2 - Frontend**
```bash
cd frontend
npm run dev
```
Expected: `Local: http://localhost:5173`

**Terminal 3 - Ollama (should already be running)**
```bash
ollama serve
```
Expected: Listening on `http://127.0.0.1:11434`

### Access Application
Open browser: **http://localhost:5173**

---

## What's Included

### Backend (FastAPI)
- ✓ User authentication (register/login)
- ✓ JWT token-based authorization
- ✓ PDF document upload & management
- ✓ Chat interface with Ollama integration
- ✓ RAG (Retrieval Augmented Generation) pipeline
- ✓ SQLite database with full schema
- ✓ Multi-tenant support

### Frontend (React + TypeScript)
- ✓ Login/Register pages
- ✓ Dashboard
- ✓ Document upload
- ✓ Chat interface
- ✓ API client configuration

### AI Integration
- ✓ Ollama API connected
- ✓ qwen3-coder:480b-cloud model
- ✓ Vector embeddings (FAISS)
- ✓ Document RAG indexing

---

## Test Credentials
```
Email: testuser@example.com
Password: testpassword123
```

Or create your own account via registration page.

---

## API Endpoints

### Authentication
```
POST /api/auth/register
POST /api/auth/login
```

### Documents
```
POST /api/documents/upload
GET /api/documents/list
PUT /api/documents/edit/{id}
DELETE /api/documents/delete/{id}
```

### Chat
```
POST /api/chat/query
GET /api/chat/sessions
GET /api/chat/messages/{session_id}
```

---

## Features

1. **User Registration & Login**
   - Email/password authentication
   - JWT tokens with 24h expiration
   - Session management

2. **Document Management**
   - Upload PDF files
   - Auto-extract text content
   - Store in database
   - Edit/delete documents
   - Tenant isolation

3. **Chat with AI**
   - Ask questions to Ollama
   - Get responses from qwen3-coder:480b
   - Chat history saved
   - Multi-turn conversations

4. **RAG (Retrieval Augmented Generation)**
   - Index documents with FAISS
   - Semantic search
   - Context-aware responses
   - Document-specific answers

---

## Technology Stack

**Backend**
- FastAPI
- SQLAlchemy
- SQLite
- LangChain
- FAISS
- Ollama API
- PyJWT

**Frontend**
- React
- TypeScript
- Vite
- Tailwind CSS
- Axios

**AI/ML**
- Ollama (qwen3-coder:480b-cloud)
- FAISS embeddings
- LangChain RAG

---

## File Structure

```
MindDoc AI/
├── app/
│   ├── api/
│   │   ├── auth.py
│   │   ├── documents.py
│   │   └── chat.py
│   ├── core/
│   │   ├── config.py
│   │   └── security.py
│   ├── database/
│   │   └── models.py
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── document_service.py
│   │   ├── rag_service.py
│   │   └── ollama_client.py
│   └── main.py
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── api.ts
│   │   └── App.tsx
│   └── package.json
├── scripts/
│   ├── test_api.py
│   └── test_ollama_http.py
├── requirements.txt
├── README.md
├── PROJECT_STATUS.md
└── FINAL_EXECUTION_REPORT.txt
```

---

## Environment Variables (Optional)

```env
OLLAMA_MODEL=qwen3-coder:480b-cloud
OLLAMA_API_URL=http://127.0.0.1:11434/api/generate
DATABASE_URL=sqlite:///./minddoc.db
JWT_SECRET=your-secret-key
```

---

## Troubleshooting

### Backend won't start
- Check if port 8000 is available
- Ensure Python dependencies: `pip install -r requirements.txt`
- Check database permissions

### Ollama not responding
- Start Ollama: `ollama serve`
- Check port 11434: `http://127.0.0.1:11434/api/tags`
- Verify model: `ollama list` (should show qwen3-coder:480b-cloud)

### Frontend won't load
- Check if port 5173 is available
- Install dependencies: `npm install`
- Clear cache: `npm cache clean --force`

### Chat not working
- Verify Ollama is running
- Check API logs for errors
- Ensure model is loaded: `ollama list`

---

## Next Steps for Production

1. [ ] Deploy to cloud (AWS/Azure/GCP)
2. [ ] Use persistent database (PostgreSQL)
3. [ ] Set up Pinecone/Weaviate for embeddings
4. [ ] Add error logging (Sentry)
5. [ ] Enable HTTPS/SSL
6. [ ] Set up CI/CD pipeline
7. [ ] Add rate limiting
8. [ ] User analytics
9. [ ] Support more LLM models
10. [ ] Advanced search features

---

## Support

For issues or questions:
1. Check the logs in terminal
2. Review API responses
3. Test endpoints with curl/Postman
4. Check Ollama status: `curl http://127.0.0.1:11434/api/tags`

---

## Project Summary

- **Status**: ✓ Complete
- **All Tests**: ✓ Passing
- **Ollama Integration**: ✓ Working
- **Chat Functionality**: ✓ Verified
- **Document Management**: ✓ Ready
- **Ready for Use**: ✓ YES

Enjoy your AI-powered document chatbot!
