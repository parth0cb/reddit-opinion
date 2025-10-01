# Reddit Opinion

Reddit Opinion is a full-stack web application that provides AI-powered analysis of Reddit discussions on any topic. Users can ask questions and receive informed opinions backed by relevant Reddit content, with proper citations to the original sources.

## Demo

https://github.com/user-attachments/assets/a8d4681f-0c16-4fc0-8069-9a39574e1b99

## How It Works

1. **Query Input**: Users enter a question or topic they want to explore
2. **Reddit Search**: The application searches Reddit for relevant discussions
3. **Content Extraction**: It extracts posts and comments from the most relevant Reddit threads
4. **AI Analysis**: Using a language model of your choice, it analyzes the content and generates a comprehensive response
5. **Citations**: All information is properly cited with links back to the original Reddit sources

## Architecture

The application consists of:
- **Frontend**: React.js application for the user interface
- **Backend**: FastAPI Python server handling API requests
- **LLM Integration**: Connects to any OpenAI-compatible API (OpenAI, Local Models, etc.)

## Features

- 🔍 **Smart Search**: Finds the most relevant Reddit discussions for any query
- 🤖 **AI-Powered Analysis**: Uses language models to synthesize information
- 📚 **Proper Citations**: All claims are backed by links to original Reddit sources
- ⚡ **Real-time Streaming**: Responses stream in real-time as they're generated
- 🛑 **Cancellation Support**: Ability to cancel ongoing queries
- 🔐 **Secure Authentication**: JWT-based authentication system
- 📊 **Token Usage Tracking**: Monitor input and output token consumption

## Prerequisites

### Backend
- Python 3.8+
- pip (Python package manager)

### Frontend
- Node.js 14+
- npm (Node package manager)

## Setup Instructions

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the backend server:
   ```bash
   uvicorn main:app
   ```
   
   The backend will start on `http://localhost:8000`

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm start
   ```
   
   The frontend will start on `http://localhost:3000`

## Usage

1. Open your browser and navigate to `http://localhost:3000`
2. Enter your LLM credentials:
   - **API Key**: Your LLM API key
   - **Base URL**: API endpoint (default: `https://api.openai.com/v1`)
   - **Model**: Model name (default: `gpt-3.5-turbo`)
3. Ask a question in the query box (e.g., "What are the best practices for remote work?")
4. Watch as the application finds relevant Reddit discussions and generates an informed response
5. All information in the response will be cited with links to the original Reddit sources

## API Endpoints

- `POST /auth/login` - Authenticate and get JWT token
- `GET /auth/verify` - Verify authentication token
- `POST /query` - Submit a query for processing (streaming response)
- `POST /query/stop` - Cancel an ongoing query

## Technologies Used

### Backend
- **FastAPI**: High-performance Python web framework
- **PyJWT**: JWT token handling
- **HTTPx**: Async HTTP client
- **BeautifulSoup4**: HTML parsing for Reddit content
- **Sentence-Transformers**: Semantic similarity analysis
- **PyTorch**: Machine learning framework
- **DDGS**: DuckDuckGo search integration

### Frontend
- **React**: JavaScript library for building user interfaces
- **Axios**: HTTP client for API requests
- **JWT-decode**: Library for decoding JWT tokens
- **DOMPurify**: HTML sanitization
- **Markdown-it**: Markdown to HTML conversion

## Project Structure

```
reddit-opinion/
├── backend/
│   ├── main.py          # FastAPI application entry point
│   ├── auth.py          # Authentication handling
│   ├── models.py        # Pydantic models
│   ├── query.py         # Query processing logic
│   ├── utils.py         # Utility functions
│   └── requirements.txt # Python dependencies
└── frontend/
    ├── src/
    │   ├── App.js       # Main application component
    │   ├── App.css      # Application styles
    │   └── index.js     # Entry point
    ├── public/
    └── package.json     # Node.js dependencies
```

## Development

### Backend Development

The backend is built with FastAPI, which provides automatic API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Frontend Development

The frontend is built with React and uses:
- Functional components with hooks
- Axios for HTTP requests
- JWT for authentication
- Markdown rendering for responses

## License

MIT License
