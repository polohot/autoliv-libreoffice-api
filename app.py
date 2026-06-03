import os
import time
import uuid
import subprocess
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from util import convert_to_pdf

ALLOWED_EXTENSIONS = {".xls", ".xlsx", ".xlsm", ".ppt", ".pptx"}
TEMP_DIR = "/tmp/lo_api"
os.makedirs(TEMP_DIR, exist_ok=True)

lo_process = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Launch LibreOffice headless server
    global lo_process
    print("Starting LibreOffice API server...")
    lo_process = subprocess.Popen([
        'libreoffice', '--headless', '--nologo', '--nodefault',
        '--accept=socket,host=localhost,port=2002;urp;'
    ])
    time.sleep(3) # Wait for server to bind to port
    yield
    # Shutdown: Terminate LibreOffice
    if lo_process:
        print("Shutting down LibreOffice API server...")
        lo_process.terminate()

app = FastAPI(title="Autoliv LibreOffice API", lifespan=lifespan)

@app.get("/health")
def health():
    return {"status": "healthy"}

def cleanup_files(*file_paths):
    """Deletes temporary files after the response is sent."""
    for path in file_paths:
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception as e:
                print(f"Failed to delete {path}: {e}")

@app.post("/convert")
def convert_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed: {ALLOWED_EXTENSIONS}")

    # Generate unique filenames to prevent collisions
    job_id = str(uuid.uuid4())
    input_path = os.path.join(TEMP_DIR, f"{job_id}{ext}")
    output_path = os.path.join(TEMP_DIR, f"{job_id}.pdf")

    # Save uploaded file to disk
    with open(input_path, "wb") as buffer:
        buffer.write(file.file.read())

    # Convert
    success = convert_to_pdf(input_path, output_path)

    if not success or not os.path.exists(output_path):
        cleanup_files(input_path, output_path)
        raise HTTPException(status_code=500, detail="Conversion failed.")

    # Schedule cleanup AFTER the file is sent to the client
    background_tasks.add_task(cleanup_files, input_path, output_path)

    return FileResponse(
        path=output_path, 
        filename=os.path.splitext(file.filename)[0] + ".pdf",
        media_type="application/pdf"
    )