import os

from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "docs")
PERSIST_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "chroma_db")

_retriever = None


def _load_documents() -> list[Document]:
    documents = []
    for filename in sorted(os.listdir(DOCS_DIR)):
        if filename.endswith(".txt"):
            path = os.path.join(DOCS_DIR, filename)
            with open(path) as f:
                content = f.read()
            documents.append(Document(page_content=content, metadata={"source": filename}))
    return documents


def _build_retriever():
    documents = _load_documents()
    splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=50)
    chunks = splitter.split_documents(documents)
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = Chroma.from_documents(chunks, embeddings, persist_directory=PERSIST_DIR)
    return vectorstore.as_retriever(search_kwargs={"k": 3})


def get_retriever():
    global _retriever
    if _retriever is None:
        _retriever = _build_retriever()
    return _retriever


def retrieve(query: str) -> list[dict]:
    docs = get_retriever().invoke(query)
    return [
        {"page_content": doc.page_content, "source": doc.metadata.get("source", "")}
        for doc in docs
    ]
