# FitZone Chatbot reorganization script
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\pc\Desktop\FitZone Chatbot"

# Step 1: Remove old .py files from git tracking
Write-Host "=== Step 1: Removing old .py files from git ==="
$files = @(
    "api.py", "config.py", "fitness_agent.py", "knowledge_retriever.py",
    "safety.py", "input_validation.py", "open_food_facts.py",
    "logging_utils.py", "retry_utils.py", "healthcheck.py", "streamlit_app.py"
)
foreach ($f in $files) {
    Write-Host "  Processing $f"
    git rm --cached $f 2>&1
    Write-Host "  Done: $f"
}

# Step 2: Create src/__init__.py
Write-Host "=== Step 2: Creating src/__init__.py ==="
New-Item -ItemType File -Path "src\__init__.py" -Force | Out-Null
Write-Host "Created src\__init__.py"

# Step 3: Move Knowledge_db contents to knowledge
Write-Host "=== Step 3: Moving Knowledge_db to knowledge ==="
Move-Item -Path "Knowledge_db\*" -Destination "knowledge\" -Force
Write-Host "Moved contents"

# Step 4: Update .gitignore
Write-Host "=== Step 4: Updating .gitignore ==="
$gitignore = @"
.env
knowledge/*.pdf
knowledge/gym_calculations.txt
.cache/
logs/
__pycache__/
*.py[cod]
.venv/
venv/
.pytest_cache/
"@
Set-Content -Path ".gitignore" -Value $gitignore
Write-Host "Updated .gitignore"

# Step 5: Delete junk files
Write-Host "=== Step 5: Deleting junk files ==="
$junkFiles = @("FIXES_STATUS.md", "run_tests.py", "run_tests.bat")
foreach ($j in $junkFiles) {
    if (Test-Path $j) {
        Remove-Item -Path $j -Force
        Write-Host "  Deleted $j"
    }
}
$junkDirs = @("__pycache__", ".pytest_cache", ".cache", "logs", "Knowledge_db", "src\__pycache__", "tests\__pycache__")
foreach ($d in $junkDirs) {
    if (Test-Path $d) {
        Remove-Item -Path $d -Recurse -Force
        Write-Host "  Deleted $d"
    }
}

# Step 6: Update Dockerfile
Write-Host "=== Step 6: Updating Dockerfile ==="
$dockerfile = @"
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=7860

WORKDIR /app

RUN apt-get update `
    && apt-get install -y --no-install-recommends build-essential `
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY knowledge/ ./knowledge/
COPY scripts/ ./scripts/

# Build the knowledge index at image build time so startup is instant
RUN python scripts/rebuild_knowledge.py

EXPOSE 7860

CMD ["sh", "-c", "uvicorn src.api:app --host 0.0.0.0 --port `${PORT:-7860}"]
"@
Set-Content -Path "Dockerfile" -Value $dockerfile
Write-Host "Updated Dockerfile"

# Step 7: Update render.yaml
Write-Host "=== Step 7: Updating render.yaml ==="
$render = Get-Content "render.yaml" -Raw
$render = $render -replace "uvicorn api:app", "uvicorn src.api:app"
Set-Content -Path "render.yaml" -Value $render
Write-Host "Updated render.yaml"

Write-Host "=== Done ==="
