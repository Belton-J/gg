import os
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from langchain.schema import AIMessage, HumanMessage
from langchain_core.prompts import PromptTemplate
from langchain_community.vectorstores import FAISS
from gtts import gTTS
import assemblyai as aai


load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# 🔐 Set your AssemblyAI API Key
aai.settings.api_key =   # 🔁 Replace with real key

# Initialize shared objects
_embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
_model = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
_index_path = "faiss_index"                       
memory = []

TEMP_DIR = "temp_audio"
os.makedirs(TEMP_DIR, exist_ok=True)

def extract_text_from_pdfs(pdf_files):
    text = ""
    for file in pdf_files:
        pdf_reader = PdfReader(file)
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
    return text

def chunk_text(text, chunk_size=1000, chunk_overlap=100):
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return splitter.split_text(text)

def save_vectors_simple(chunks):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vector_store = FAISS.from_texts(chunks, embedding=embeddings)

    index_path = "faiss_index"
    vector_store.save_local(index_path)


def get_chat_response(question: str) -> str:
    if not os.path.exists(os.path.join(_index_path, "index.faiss")):
        raise ValueError("Vector store not found.")

    vectordb = FAISS.load_local(_index_path, _embeddings, allow_dangerous_deserialization=True)
    retriever = vectordb.as_retriever()

    # Build context from previous messages
    chat_context = ""
    for msg in memory:
        role = "You" if isinstance(msg, HumanMessage) else "Bot"
        chat_context += f"{role}: {msg.content}\n"
    chat_context += f"You: {question}"

    prompt = PromptTemplate(
        template="""
You are a helpful assistant. Use the context chunks to answer the user's question clearly.
If the answer is not in the context, say so. Use prior conversation to improve relevance.

Context:
{context}

Chat History:
{history}

Current Question:
{question}

Answer:""",
        input_variables=["context", "history", "question"]
    )

    docs = retriever.get_relevant_documents(question)
    context_text = "\n\n".join([doc.page_content for doc in docs])

    model = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
    chain = (
    {
        "context": lambda x: x["context"],
        "question": lambda x: x["question"],
        "history": lambda x: x["history"]
    }
    | prompt
    | model
)

    result = chain.invoke({
    "context": context_text,
    "history": chat_context,
    "question": question
    })

    memory.append(HumanMessage(content=question))
    memory.append(AIMessage(content=result.content))  # ✅ Only the text
    return result.content



# 🔊 Transcribe using AssemblyAI
def transcribe_with_assemblyai(audio_path):
    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(audio_path)
    if not transcript.text.strip():
        raise ValueError("No speech recognized.")
    return transcript.text.strip()

# 🗣️ Convert text to audio using gTTS
def text_to_speech(text, filename):
    TEMP_DIR = "temp_audio"
    os.makedirs(TEMP_DIR, exist_ok=True)
    output_path = os.path.join(TEMP_DIR, filename)
    gTTS(text).save(output_path)
    return output_path
