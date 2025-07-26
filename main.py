# === main.py ===
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import uuid
from utils import (
    extract_text_from_pdfs,
    chunk_text,
    save_vectors_simple,
    transcribe_with_assemblyai,
    classify_question,
    get_chat_response,
    friendly_agent
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMP_DIR = "temp_audio"
os.makedirs(TEMP_DIR, exist_ok=True)

@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    try:
        text = extract_text_from_pdfs([file.file])
        chunks = chunk_text(text)
        save_vectors_simple(chunks)
        return {"message": "PDF processed and stored in vector DB."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@app.post("/voice-chat")
async def voice_chat(audio: UploadFile = File(...)):
    try:
        uid = str(uuid.uuid4())
        input_audio_path = os.path.join(TEMP_DIR, f"{uid}.wav")
        with open(input_audio_path, "wb") as f:
            f.write(await audio.read())

        question_text = transcribe_with_assemblyai(input_audio_path)
        route = classify_question(question_text)

        if route == "pdf":
            answer_text = get_chat_response(question_text)
        else:
            answer_text = friendly_agent(question_text)

        return JSONResponse({"transcribed": question_text, "answer": answer_text})

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chat")
async def text_chat(question: str):
    try:
        route = classify_question(question)

        if route == "pdf":
            answer_text = get_chat_response(question)
        else:
            answer_text = friendly_agent(question)

        return JSONResponse({"question": question, "answer": answer_text})

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
