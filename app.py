import os
import re
import tempfile
import logging
from pathlib import Path
from typing import Optional
 
import pdfplumber
from docx import Document
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
 
import llm_analyzer
 
load_dotenv(override=True)
 
# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)
 
# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="CVInsight API", version="2.0.0")
 
# CORS must come BEFORE static file mount
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
BASE_DIR     = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")
 
# ── Constants ─────────────────────────────────────────────────────────────────
ALLOWED_EXTENSIONS = {"pdf", "docx"}
MAX_FILE_SIZE_MB   = 5
MAX_FILE_SIZE_B    = MAX_FILE_SIZE_MB * 1024 * 1024
 
STOPWORDS = {
    "the", "and", "is", "in", "to", "of", "a", "an", "for", "on", "at",
    "by", "with", "as", "be", "we", "are", "our", "you", "your",
    "looking", "have", "will", "that", "this", "from", "or", "not",
}
 
SKILLS = [
    ("Python",           [r"\bpython\b"]),
    ("Java",             [r"\bjava\b"]),
    ("C++",              [r"c\+\+", r"\bcpp\b"]),
    ("JavaScript",       [r"\bjavascript\b", r"\bjs\b"]),
    ("TypeScript",       [r"\btypescript\b", r"\bts\b"]),
    ("React",            [r"\breact\b", r"\breactjs\b"]),
    ("Node.js",          [r"\bnode\.?js\b", r"\bnodejs\b"]),
    ("SQL",              [r"\bsql\b"]),
    ("Machine Learning", [r"\bmachine\s+learning\b", r"\bml\b"]),
    ("Deep Learning",    [r"\bdeep\s+learning\b"]),
    ("Docker",           [r"\bdocker\b"]),
    ("Git",              [r"\bgit\b"]),
]
 
ROLE_RULES = [
    ("Data Scientist",      [r"\bmachine\s+learning\b", r"\bdeep\s+learning\b", r"\bdata\s+science\b"]),
    ("Frontend Developer",  [r"\breact\b", r"\bvue\b", r"\bangular\b", r"\bjavascript\b", r"\btypescript\b"]),
    ("Backend Developer",   [r"\bpython\b", r"\bnode\.?js\b", r"\bfastapi\b", r"\bdjango\b", r"\bflask\b"]),
    ("Java Developer",      [r"\bjava\b"]),
    ("Full Stack Developer",[r"\bfull.?stack\b"]),
    ("DevOps Engineer",     [r"\bdocker\b", r"\bkubernetes\b", r"\bci.?cd\b", r"\bjenkins\b"]),
]

SECTION_RULES = [
    ("project",      10, "Include a Projects section showcasing your work."),
    ("experience",   15, "Add work or internship experience to strengthen your profile."),
    ("education",    10, "Include your education details (degree, institution, year)."),
    ("certification", 5, "Add certifications or relevant coursework."),
    ("contact",       5, "Add contact details such as email, LinkedIn, or GitHub."),
    ("summary",       5, "Add a short summary or objective to clarify your focus."),
]

ACHIEVEMENT_PATTERNS = [
    r"\b(achieved|improved|reduced|increased|built|designed|implemented|optimized|deployed|launched|managed)\b",
    r"\b\d+%\b",
    r"\b\d+\s*(?:x|times|year|years|months|weeks)\b",
    r"\$\d+",
]

ACTION_VERBS = [
    "led", "managed", "built", "designed", "implemented", "optimized", "launched", "created", "developed",
    "automated", "improved", "reduced", "increased", "collaborated", "tested", "deployed", "maintained"
]

# ── Global error handler ──────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    log.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again."},
    )
 
# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/")
def home():
    return FileResponse(FRONTEND_DIR / "index.html")
 
@app.get("/health")
def health():
    return {
        "status":     "ok",
        "ai_enabled": llm_analyzer.is_ai_enabled(),
    }
 
# ── Text extraction ───────────────────────────────────────────────────────────
def _get_extension(filename: str) -> str:
    parts = filename.rsplit(".", 1)
    return parts[-1].lower() if len(parts) == 2 else ""
 
 
async def extract_text(file: UploadFile) -> str:
    ext = _get_extension(file.filename or "")
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '.{ext}'. Please upload a PDF or DOCX.",
        )
 
    content = await file.read()
    if len(content) > MAX_FILE_SIZE_B:
        raise HTTPException(status_code=413, detail=f"File exceeds the {MAX_FILE_SIZE_MB} MB limit.")
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
 
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        return _extract_pdf(tmp_path) if ext == "pdf" else _extract_docx(tmp_path)
    except HTTPException:
        raise
    except Exception as exc:
        log.error("Text extraction failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=422, detail="Could not read the file. It may be corrupted or password-protected.")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
 
 
def _extract_pdf(path: str) -> str:
    pages = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
    return "\n".join(pages)
 
 
def _extract_docx(path: str) -> str:
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
 
 
# ── Helpers ───────────────────────────────────────────────────────────────────
def _matches_any(patterns: list[str], text: str) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)
 
def clean_words(text: str) -> list[str]:
    return re.findall(r'\b[a-z][a-z0-9]*\b', text.lower())
 
 
# ── Job matching ──────────────────────────────────────────────────────────────
def match_job(resume_text: str, job_desc: str) -> dict:
    resume_words = set(clean_words(resume_text))
    job_words = {
        w for w in clean_words(job_desc)
        if w not in STOPWORDS and len(w) > 2
    }
    if not job_words:
        return {"match_percentage": 0, "missing_keywords": []}
    common    = resume_words & job_words
    match_pct = min(int(len(common) / len(job_words) * 100), 100)
    missing   = sorted(job_words - resume_words, key=len, reverse=True)[:10]
    return {"match_percentage": match_pct, "missing_keywords": missing}
 
 
# ── Main endpoint ─────────────────────────────────────────────────────────────
@app.post("/analyze")
async def analyze(
    file:     UploadFile    = File(...),
    job_desc: Optional[str] = Form(None),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file received.")
 
    log.info("Analyzing: %s", file.filename)
    text = await extract_text(file)
 
    if not text.strip():
        raise HTTPException(
            status_code=422,
            detail="No text could be extracted. If this is a scanned PDF, text extraction is not supported yet.",
        )
 
    result = llm_analyzer.analyze_resume(text, job_desc)
    if result is None:
        log.error("AI analysis unavailable; manual fallback disabled")
        raise HTTPException(
            status_code=503,
            detail="AI analysis unavailable. Ensure GROQ_API_KEY is set and the model is reachable.",
        )
    log.info("AI analysis complete. Score=%s", result["score"])
    if not result.get("skills"):
        result["skills"] = [
            name for name, patterns in SKILLS if _matches_any(patterns, text.lower())
        ]
 
    if job_desc and job_desc.strip():
        result.update(match_job(text, job_desc.strip()))
 
    log.info("Done. Score=%s | AI=%s", result["score"], result.get("ai_powered"))
    return result
