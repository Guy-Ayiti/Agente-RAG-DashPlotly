# import basics
import io
import os
import time
from dotenv import load_dotenv

# import pinecone
from pinecone import Pinecone, ServerlessSpec

# import langchain
from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

#documents
from langchain_community.document_loaders import PyPDFDirectoryLoader #, PyPDFLoader, PDFPlumberLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter


def IngestData(data:str):
    load_dotenv()

    pinecone = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))

    # initialize pinecone database
    index_name = os.environ.get("PINECONE_INDEX_NAME")

    # check whether index exists, and create if not
    existing_indexes = [index_info["name"] for index_info in pinecone.list_indexes()]

    if index_name not in existing_indexes:
        pinecone.create_index(
            name=index_name,
            dimension=1024,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        while not pinecone.describe_index(index_name).status["ready"]:
            time.sleep(1)

    index = pinecone.Index(index_name)


    # Clear existing vectors in the index (OverWrite behavior)
    stats = index.describe_index_stats()
    total_vectors = stats.get("total_vector_count", 0)
    if total_vectors > 0:
        print(f"Clearing {total_vectors} existing vectors from index '{index_name}'...")
        index.delete(delete_all=True)



    # initialize embeddings model + vector store
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large",
                                  api_key=os.environ.get("OPENAI_API_KEY"),
                                  dimensions=1024)

    vector_store = PineconeVectorStore(index=index, embedding=embeddings)

    # loading the PDF document
                                                # pdf_stream = io.BytesIO(data)        
    loader = PyPDFDirectoryLoader("Documents/") # loader = PDFPlumberLoader(pdf_stream)     
    raw_documents = loader.load()               # print('RAW DOCUMENT :', raw_documents)

    # splitting the document
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=400,
        length_function=len,
        is_separator_regex=False,
    )
    
    # creating the chunks
    documents = text_splitter.split_documents(raw_documents)

    # generate unique id's
    i = 0
    uuids = []
    while i < len(documents):
        i += 1
        uuids.append(f"id{i}")

    # add to database
    vector_store.add_documents(documents=documents, ids=uuids)
    return None

#IngestData(b"estoy aqui")






