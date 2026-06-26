"""One-time reorganization script for FitZone Chatbot."""
import os
import shutil
import subprocess

BASE = r"C:\Users\pc\Desktop\FitZone Chatbot"
os.chdir(BASE)

# Step 1: Remove old .py files from git tracking
print("=== Step 1: Removing old .py files from git ===")
files = [
    "api.py", "config.py", "fitness_agent.py", "knowledge_retriever.py",
    "safety.py", "input_validation.py", "open_food_facts.py",
    "logging_utils.py", "retry_utils.py", "healthcheck.py", "streamlit_app.py"
]
for f in files:
    print(f"  git rm --cached {f}")
    subprocess.run(["git", "rm", "--cached", f], check=False)

# Step 2: Create src/__init__.py
print("=== Step 2: Creating src/__init__.py ===")
with open(os.path.join("src", "__init__.py"), "w") as f:
    f.write("")
print("Created src/__init__.py")

# Step 3: Move Knowledge_db contents to knowledge
print("=== Step 3: Moving Knowledge_db to knowledge ===")
kb_src = os.path.join(BASE, "Knowledge_db")
kb_dst = os.path.join(BASE, "knowledge")
if os.path.isdir(kb_src):
    for item in os.listdir(kb_src):
        src = os.path.join(kb_src, item)
        dst = os.path.join(kb_dst, item)
        if os.path.exists(dst):
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            else:
                os.remove(dst)
        shutil.move(src, dst)
        print(f"  Moved {item}")
    # Remove empty Knowledge_db
    os.rmdir(kb_src)
    print("Removed empty Knowledge_db")

# Step 4: Delete junk files
print("=== Step 4: Deleting junk files ===")
junk_files = ["FIXES_STATUS.md", "run_tests.py", "run_tests.bat", "_reorganize.ps1", "_reorganize.py"]
for j in junk_files:
    p = os.path.join(BASE, j)
    if os.path.exists(p):
        os.remove(p)
        print(f"  Deleted {j}")

junk_dirs = ["__pycache__", ".pytest_cache", ".cache", "logs", "src\\__pycache__", "tests\\__pycache__"]
for d in junk_dirs:
    p = os.path.join(BASE, d)
    if os.path.exists(p):
        shutil.rmtree(p)
        print(f"  Deleted {d}")

print("=== Done ===")
