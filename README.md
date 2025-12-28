# MindDoc AI

A cutting-edge full-stack RAG (Retrieval-Augmented Generation) application for document Q&A using advanced AI, powered by DeepSeek-V3 for intelligent, fast, and responsive conversations.

## Features

- **User Authentication**: Secure register/login with multi-tenant architecture
- **Document Upload**: Support for PDF, DOCX, and image files (PNG, JPG, JPEG, TIFF, BMP) with OCR capabilities
- **AI-Powered Chat**: Integrated with DeepSeek-V3.1:671b-cloud for superior reasoning and response quality
- **RAG Technology**: Intelligent document processing with vector embeddings for context-aware answers
- **Editable Sessions & Documents**: Full CRUD operations on chat sessions, documents, and saved items
- **Saved Items**: Star documents and responses for quick access
- **Beautiful UI**: Astonishing frontend with gradients, animations, and professional design
- **Robust Backend**: Error-resistant server handling any PDF or query
- **Settings Management**: Update user email and account settings

## Setup

1. Install Python 3.11+ and Node.js 18+.

2. Clone or extract the project.

3. Set environment variables:
   - `OPENAI_API_KEY` (fallback)
   - `DEEPSEEK_API_KEY` (primary AI model)

4. For backend: `pip install -r requirements.txt`

5. For frontend: `cd frontend && npm install`

6. Run `start.bat` to launch both services.

7. Open http://127.0.0.1:5173

## Usage

- Register/Login to your account
- Upload documents (PDFs, images, etc.) via Upload page or directly in Chat
- Start chatting: Ask general questions or attach specific documents for context
- Manage sessions: Edit titles, delete sessions
- Save important documents and responses with star feature
- Access settings to update email

## Architecture

- **Backend**: FastAPI with SQLAlchemy, ChromaDB for vectors, DeepSeek API integration
- **Frontend**: React with TypeScript, Tailwind CSS for stunning UI
- **AI**: DeepSeek-V3 for chat, sentence-transformers for embeddings
- **OCR**: Tesseract for image text extraction