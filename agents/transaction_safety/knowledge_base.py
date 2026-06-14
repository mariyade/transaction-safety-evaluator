import os

from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "docs")
PERSIST_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "chroma_db", "transaction_safety_sections_v1")
RETRIEVAL_K = 2

_retriever = None


def _section_documents(content: str, filename: str) -> list[Document]:
    sections = [section.strip() for section in content.split("\n\n") if section.strip()]
    return [
        Document(
            page_content=section,
            metadata={"source": filename, "section": section.splitlines()[0]},
        )
        for section in sections
        if len(section.splitlines()) > 1
    ]


def _load_documents() -> list[Document]:
    documents = []
    for filename in sorted(os.listdir(DOCS_DIR)):
        if filename.endswith(".txt"):
            path = os.path.join(DOCS_DIR, filename)
            with open(path) as f:
                content = f.read()
            documents.extend(_section_documents(content, filename))
    return documents


def _build_retriever():
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    if os.path.exists(PERSIST_DIR):
        vectorstore = Chroma(persist_directory=PERSIST_DIR, embedding_function=embeddings)
        if vectorstore._collection.count() > 0:
            return vectorstore.as_retriever(search_kwargs={"k": RETRIEVAL_K})
    documents = _load_documents()
    vectorstore = Chroma.from_documents(documents, embeddings, persist_directory=PERSIST_DIR)
    return vectorstore.as_retriever(search_kwargs={"k": RETRIEVAL_K})


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
