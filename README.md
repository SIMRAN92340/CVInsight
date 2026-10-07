# CVInsight - Resume Analyzer

A modern AI-powered resume analyzer that provides scoring, skill detection, job role matching, and LLM-based insights.

## 🚀 Quick Start

### 1.  Prerequisites
- Python 3.8+
- Dependencies installed (see `requirements.txt`)

### 2. Run the Application

**Option A: Using PowerShell Script (Windows)**
```powershell
.\run.ps1
```

**Option B: Manual Startup**
```bash
# Activate virtual environment
.\.venv\Scripts\Activate.ps1  # Windows
source .venv/bin/activate     # Linux/Mac

# Run the server
uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Access the Application
Open your browser and navigate to: **http://127.0.0.1:8000**

## 📋 Features

### Resume Analysis
- **Score Calculation**: Evaluates resume quality (0-100)
- **Skill Detection**: Identifies technical skills (Python, Java, React, etc.)
- **Section Validation**: Checks for essential resume sections
- **Length Analysis**: Recommends optimal resume length

### Job Matching (Optional)
- Paste a job description to get match percentage
- Identifies missing keywords from the job posting
- Suggestions for improvement

### AI Insights (Groq LLM)
- Deep analysis using Groq's language model
- Returns structured insights including:
  - Summary
  - Strengths
  - Skills highlighted
  - Experience highlights
  - Improvement suggestions

## 📁 Project Structure

```
Resume Analyzer/
├── app.py                 # FastAPI backend
├── llm_analyzer.py        # Groq LLM integration
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables
├── run.ps1               # Windows run script
├── frontend/
│   ├── index.html        # Main UI
│   ├── script.js         # Interactive logic
│   └── styles.css        # Styling

```

## 🔑 Environment Setup

The `.env` file contains:
```
GROQ_API_KEY=your_groq_api_key_here
MODEL_NAME = "llama-3.3-70b-versatile"
```

**Get your Groq API Key:**
1. Go to [Groq Console](https://console.groq.com)
2. Create an account and generate an API key
3. Add it to `.env` as `GROQ_API_KEY=gsk_...`

## 📤 Supported Formats

- **PDF** (.pdf)
- **DOCX** (.docx)
- Maximum file size: **5 MB**

## 🎯 API Endpoints

### POST /analyze
Analyzes a resume with optional job description.

**Request:**
```
multipart/form-data:
  - file: [PDF/DOCX file]
  - job_desc: [Optional job description text]
```

**Response:**
```json
{
  "score": 82,
  "summary": "Strong backend-focused resume with relevant technical skills.",
  "strengths": [
    "Clear project experience",
    "Good technical stack alignment"
  ],
  "improvement_suggestions": [
    "Add more quantified achievements",
    "Improve keyword alignment"
  ],
  "skills": [
    "Python",
    "FastAPI",
    "React"
  ],
  "suggested_roles": [
    "Backend Developer",
    "Full Stack Developer"
  ],
  "match_percentage": 78,
  "missing_keywords": [
    "Docker",
    "CI/CD"
  ],
  "ai_powered": true
}
```

### GET /health
Health check endpoint.

## 🛠️ Development

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Testing
No automated tests are defined in this repository yet. Start the backend and verify the `/analyze` and `/health` endpoints manually.

## 📝 Notes

- The app uses local regex-based skill detection for fast, accurate results
- Groq LLM provides detailed insights but may take a few seconds
- CORS is enabled for frontend-backend communication

## ⚠️ Security

- Never commit `.env` with real API keys
- The API key is validated on startup
- Consider tightening CORS origins in production

## 🐛 Troubleshooting

**"Cannot reach the backend"**
- Ensure the server is running on `http://127.0.0.1:8000`
- Check firewall settings

**"API key error"**
- Verify `GROQ_API_KEY` is set correctly in `.env`
- Keys should start with `gsk_`

**"File extraction failed"**
- Check file format (must be PDF or DOCX)
- File should not be password-protected
- Try uploading a different file

---

Built with FastAPI, Groq, and modern frontend technologies.
