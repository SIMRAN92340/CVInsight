// ── File Input Handling ──────────────────────────────────────────────────────

const fileInput   = document.getElementById('fileInput');
const uploadCard  = document.getElementById('uploadCard');
const fileNameEl  = document.getElementById('fileName');
const analyzeBtn  = document.getElementById('analyzeBtn');

fileInput.addEventListener('change', () => {
  const file = fileInput.files[0];
  if (!file) return;
  fileNameEl.textContent = '📄 ' + file.name;
  fileNameEl.style.display = 'block';
  analyzeBtn.disabled = false;
});

// Drag & drop
uploadCard.addEventListener('dragover', e => {
  e.preventDefault();
  uploadCard.classList.add('drag-over');
});
uploadCard.addEventListener('dragleave', () => uploadCard.classList.remove('drag-over'));
uploadCard.addEventListener('drop', e => {
  e.preventDefault();
  uploadCard.classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file) {
    const dt = new DataTransfer();
    dt.items.add(file);
    fileInput.files = dt.files;
    fileNameEl.textContent = '📄 ' + file.name;
    fileNameEl.style.display = 'block';
    analyzeBtn.disabled = false;
  }
});

// ── Main Handler ─────────────────────────────────────────────────────────────

async function handleFile() {
  const file = fileInput.files[0];
  if (!file) return;

  const jobDesc = document.getElementById('jobDesc').value.trim();

  // Client-side validation
  const ext = file.name.split('.').pop().toLowerCase();
  if (!['pdf', 'docx'].includes(ext)) {
    setError('Please upload a PDF or DOCX file.');
    return;
  }
  if (file.size > 5 * 1024 * 1024) {
    setError('File is too large. Maximum allowed size is 5 MB.');
    return;
  }

  setError('');
  setLoading(true);
  hideResults();

  const formData = new FormData();
  formData.append('file', file);
  if (jobDesc) formData.append('job_desc', jobDesc);

  // Pre-flight: check server is up
  try {
    await fetch('/health', { method: 'GET' });
  } catch {
    setLoading(false);
    setError('Cannot reach the backend. Make sure you opened this page through the running FastAPI server.');
    return;
  }

  try {
    const res = await fetch('/analyze', {
      method: 'POST',
      body: formData
    });

    // Surface the backend's own error message when available
    if (!res.ok) {
      let msg = `Server error (${res.status})`;
      try {
        const err = await res.json();
        if (err.detail) msg = err.detail;
      } catch { /* ignore parse failure */ }
      throw new Error(msg);
    }

    const data = await res.json();
    console.log('Backend response:', data);

    setLoading(false);
    renderResults(data, file.name, !!jobDesc);

  } catch (err) {
    setLoading(false);
    setError(err.message || 'An unexpected error occurred. Check the console for details.');
    console.error(err);
  }
}

// ── UI State ─────────────────────────────────────────────────────────────────

function setLoading(active) {
  document.getElementById('loader').classList.toggle('active', active);
  analyzeBtn.disabled = active;

  if (active) {
    analyzeBtn.innerHTML = `
      <svg class="spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
        <path d="M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z" opacity="0.25"/>
        <path d="M21 12a9 9 0 0 0-9-9"/>
      </svg>
      Analyzing…`;
  } else {
    analyzeBtn.innerHTML = `
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
      </svg>
      Analyze Resume`;
  }
}

function setError(msg) {
  const bar = document.getElementById('errorBar');
  document.getElementById('errorMsg').textContent = msg;
  bar.classList.toggle('show', !!msg);
}

function hideResults() {
  document.getElementById('results').classList.remove('visible');
}

// ── Render Results ────────────────────────────────────────────────────────────

function renderResults(data, fileName, hasJobDesc) {
  const results = document.getElementById('results');
  results.classList.add('visible');

  document.getElementById('resultsFileName').textContent = fileName;

  // ── Score Ring ──
  const score = data.score ?? 0;
  const arc = document.getElementById('scoreArc');
  const circumference = 2 * Math.PI * 45;  // r=45 → ~283
  const offset = circumference * (1 - score / 100);

  // Animate after next frame
  setTimeout(() => {
    arc.style.strokeDashoffset = offset;
  }, 100);

  // Animate counter
  animateCounter(document.getElementById('scoreNum'), 0, score, 1200);

  // Grade
  const { grade, desc, color } = getGrade(score);
  document.getElementById('scoreGrade').textContent = grade;
  document.getElementById('scoreGrade').style.color = color;
  document.getElementById('scoreDesc').textContent  = desc;
  arc.style.stroke = color;

  // ── Metrics ──
  const suggestions   = data.improvement_suggestions ?? data.suggestions ?? [];
  const suggestedRoles = data.suggested_roles ?? [];
  const skills         = data.skills ?? [];

  document.getElementById('suggCount').textContent = suggestions.length;
  document.getElementById('rolesCount').textContent = suggestedRoles.length;

  // ── Suggestions ──
  const suggEl = document.getElementById('suggestionsList');
  suggEl.innerHTML = '';
  suggestions.forEach(s => {
    const isPositive = s.toLowerCase().includes('decent') || s.toLowerCase().includes('good') || s.toLowerCase().includes('great');
    suggEl.insertAdjacentHTML('beforeend', `
      <div class="suggestion-item">
        <div class="suggestion-icon" style="background:${isPositive ? 'rgba(200,245,90,0.12)' : 'rgba(255,190,61,0.12)'};">
          <svg viewBox="0 0 24 24" fill="none" stroke="${isPositive ? 'var(--accent)' : 'var(--amber)'}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            ${isPositive
              ? '<polyline points="20,6 9,17 4,12"/>'
              : '<line x1="12" y1="5" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>'}
          </svg>
        </div>
        <span class="suggestion-text">${s}</span>
      </div>`);
  });

  // ── Suggested Roles ──
  const suggestedRolesEl = document.getElementById('suggestedRolesList');
  suggestedRolesEl.innerHTML = '';
  if (suggestedRoles.length > 0) {
    suggestedRoles.forEach(r => {
      suggestedRolesEl.insertAdjacentHTML('beforeend', `
        <div class="role-pill">
          <span class="role-dot"></span>
          ${r}
        </div>`);
    });
  } else {
    suggestedRolesEl.innerHTML = '<div class="suggestion-text">No suggested roles were detected.</div>';
  }

  // ── Skills ──
  const skillsEl = document.getElementById('skillsList');
  skillsEl.innerHTML = '';
  if (skills.length > 0) {
    skills.forEach(r => {
      skillsEl.insertAdjacentHTML('beforeend', `
        <div class="role-pill">
          <span class="role-dot"></span>
          ${r}
        </div>`);
    });
  } else {
    skillsEl.innerHTML = '<div class="suggestion-text">No skills were detected.</div>';
  }

  // ── Job Match ──
  const jobCard = document.getElementById('jobMatchCard');
  if (hasJobDesc && data.match_percentage !== undefined) {
    jobCard.style.display = 'block';
    const pct = data.match_percentage;
    document.getElementById('matchVal').textContent = pct + '%';
    setTimeout(() => {
      document.getElementById('matchFill').style.width = pct + '%';
    }, 100);

    // Missing keywords
    const missing = data.missing_keywords ?? [];
    const missingSection = document.getElementById('missingSection');
    if (missing.length > 0) {
      missingSection.style.display = 'block';
      document.getElementById('missingKeywords').innerHTML =
        missing.map(k => `<span class="keyword-tag">${k}</span>`).join('');
    } else {
      missingSection.style.display = 'none';
    }
  } else {
    jobCard.style.display = 'none';
  }

  // ── LLM Insights (shown only when AI is active) ──
  const llmCard = document.getElementById('llmCard');
  const aiPowered = data.ai_powered === true;
  if (aiPowered && (data.summary || (data.strengths && data.strengths.length))) {
    llmCard.style.display = 'block';
    const llmContent = document.getElementById('llmContent');
    let html = '';

    if (data.summary) {
      html += `<div class="llm-item"><strong>Summary</strong><p>${data.summary}</p></div>`;
    }
    if (data.strengths && data.strengths.length > 0) {
      html += `<div class="llm-item"><strong>Strengths</strong><p>${data.strengths.join(' · ')}</p></div>`;
    }
    if (data.suggested_roles && data.suggested_roles.length > 0) {
      html += `<div class="llm-item"><strong>Suggested Roles</strong><p>${data.suggested_roles.join(' · ')}</p></div>`;
    }

    llmContent.innerHTML = html || '<p style="color:var(--muted)">No additional AI insights available.</p>';
  } else {
    llmCard.style.display = 'none';
  }

  // Smooth scroll
  results.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function getGrade(score) {
  if (score >= 80) return { grade: 'Excellent', desc: 'Your resume is strong and well-structured. A few finishing touches could make it outstanding.', color: 'var(--accent)' };
  if (score >= 60) return { grade: 'Good',      desc: 'Solid resume with clear strengths. Address the suggestions to reach the next level.', color: 'var(--blue)'  };
  if (score >= 40) return { grade: 'Fair',       desc: 'Some key sections need attention. Follow the suggestions to significantly improve your score.', color: 'var(--amber)' };
  return { grade: 'Needs Work', desc: 'Several important areas are missing or underdeveloped. Work through the suggestions below.', color: 'var(--red)' };
}

function animateCounter(el, from, to, duration) {
  const start = performance.now();
  function step(now) {
    const p = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - p, 3);
    el.textContent = Math.round(from + (to - from) * eased);
    if (p < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}