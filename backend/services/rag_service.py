from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from langchain_text_splitters import CharacterTextSplitter
from backend.config import OPENAI_API_KEY

# Sample knowledge base (you can expand later)
raw_documents = [
    "Heavy rainfall often causes river overflow leading to floods.",
    "Urbanization reduces water absorption causing waterlogging.",
    "Deforestation increases flood risk and soil erosion.",
    "Cyclones cause severe damage to coastal buildings.",
    "Earthquakes lead to structural collapse in weak buildings."
]

# Convert to LangChain documents
documents = [Document(page_content=text) for text in raw_documents]

# Split documents
text_splitter = CharacterTextSplitter(chunk_size=100, chunk_overlap=10)
docs = text_splitter.split_documents(documents)

# Create embeddings + vector DB
embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
vector_store = FAISS.from_documents(docs, embeddings)

def get_context(query: str):
    """
    Retrieves relevant knowledge based on query
    """
    results = vector_store.similarity_search(query, k=3)
    return "\n".join(doc.page_content for doc in results)