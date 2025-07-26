# === utils.py ===
import os
import pdfplumber
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_community.vectorstores import FAISS
from langchain.schema import AIMessage, HumanMessage
from langchain.memory import ConversationBufferMemory
from dotenv import load_dotenv
import assemblyai as aai

load_dotenv()

# Load API keys
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")

# Initialize clients and models
_embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
_model = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
_index_path = "faiss_index"

# === Memory ===
pdf_memory = ConversationBufferMemory(return_messages=True)
friendly_memory = ConversationBufferMemory(return_messages=True)

# === Extract text from PDF ===
def extract_text_from_pdfs(pdf_files):
    text = ""
    for file in pdf_files:
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
                text += "\n"
    return text

# === Chunk text ===
def chunk_text(text, chunk_size=800, chunk_overlap=200):
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return splitter.split_text(text)

# === Save vectors ===
def save_vectors_simple(chunks):
    vector_store = FAISS.from_texts(chunks, embedding=_embeddings)
    vector_store.save_local(_index_path)

# === Classify question ===
def classify_question(question):
    classifier_prompt = PromptTemplate(
        template="""
        Classify the question below as either 'friendly' or 'pdf'.
        If it relates to uploaded documents or technical context, return 'pdf'.
        Otherwise, return 'friendly'.

        Question:
        {question}

        Answer:
        """,
        input_variables=["question"]
    )
    chain = classifier_prompt | _model
    result = chain.invoke({"question": question})
    classification = result.content.strip().lower()
    return "pdf" if "pdf" in classification else "friendly"

# === RAG Answer ===
def get_chat_response(question: str) -> str:
    if not os.path.exists(os.path.join(_index_path, "index.faiss")):
        raise ValueError("Vector store not found.")

    vectordb = FAISS.load_local(_index_path, _embeddings, allow_dangerous_deserialization=True)
    retriever = vectordb.as_retriever()

    docs = retriever.get_relevant_documents(question)
    context_text = "\n\n".join([doc.page_content for doc in docs])

    prompt = PromptTemplate(
        template="""
        You are a helpful assistant. Use the following context to answer the question.
        If the answer isn't found in the context, say "I don't know".

        Context:
        {context}

        Chat History:
        {history}

        Question:
        {question}

        Answer:
        """,
        input_variables=["context", "history", "question"]
    )

    chain = {
        "context": lambda x: x["context"],
        "history": lambda x: x["history"],
        "question": lambda x: x["question"]
    } | prompt | _model

    chat_history = pdf_memory.load_memory_variables({})["history"]
    result = chain.invoke({
        "context": context_text,
        "history": chat_history,
        "question": question
    })

    pdf_memory.chat_memory.add_user_message(question)
    pdf_memory.chat_memory.add_ai_message(result.content)
    return result.content

# === Friendly Chat ===
def friendly_agent(question: str) -> str:
    prompt = PromptTemplate(
        template="""
        You are a friendly chatbot. Engage in light, supportive conversation.

        Chat History:
        {history}

        User: {question}
        Bot:
        """,
        input_variables=["history", "question"]
    )

    chain = {
        "history": lambda x: x["history"],
        "question": lambda x: x["question"]
    } | prompt | _model

    history = friendly_memory.load_memory_variables({})["history"]
    result = chain.invoke({
        "history": history,
        "question": question
    })

    friendly_memory.chat_memory.add_user_message(question)
    friendly_memory.chat_memory.add_ai_message(result.content)
    return result.content

# === Transcribe audio ===
def transcribe_with_assemblyai(audio_path):
    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(audio_path)
    if not transcript.text.strip():
        raise ValueError("No speech recognized.")
    return transcript.text.strip()