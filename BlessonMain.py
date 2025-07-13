
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from rag_utils import extract_text_from_pdfs, chunk_text, save_vectors_simple, get_chat_response, text_to_speech, transcribe_with_assemblyai
from fastapi import UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import uuid
import os
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔧 Setup temp folder
TEMP_DIR = "temp_audio"
os.makedirs(TEMP_DIR, exist_ok=True)

@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    try:
        # Step 1: Read file in-memory
        text = extract_text_from_pdfs([file.file])
        
        # Step 2: Chunk text
        chunks = chunk_text(text)

        # Step 3: Embed and store in FAISS (no metadata)
        save_vectors_simple(chunks)

        return {"message": "PDF processed and stored in vector DB."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")




@app.get("/chat")
async def chat(question: str):
    try:
        answer = get_chat_response(question)
        return {"question": question, "answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/voice-chat")
async def voice_chat(audio: UploadFile = File(...)):
    try:
        # Step 1: Save uploaded audio
        uid = str(uuid.uuid4())
        input_audio_path = os.path.join(TEMP_DIR, f"{uid}.wav")
        with open(input_audio_path, "wb") as f:
            f.write(await audio.read())

        # Step 2: Transcribe using AssemblyAI
        question_text = transcribe_with_assemblyai(input_audio_path)

        # Step 3: Get RAG answer
        answer_text = get_chat_response(question_text)

        # Step 4: Convert to voice
        output_audio_path = text_to_speech(answer_text, f"{uid}_reply.mp3")

        # Step 5: Return audio response
        return FileResponse(output_audio_path, media_type="audio/mpeg", filename="response.mp3")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
