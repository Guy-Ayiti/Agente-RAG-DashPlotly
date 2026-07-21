import os

from langchain_community. document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter 
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_postgres import PostgresChatMessageHistory

from dotenv import load_dotenv
load_dotenv()

from urllib.parse import quote_plus
import psycopg
from supabase import create_client



def Ingestion(path):
    # Load document 
    loader = PyPDFLoader(path)
    document = loader.load()

    # Chunk creation
    text_splitter =  RecursiveCharacterTextSplitter(chunk_size = 500, 
                                                        chunk_overlap = 200)
    chunks = text_splitter.split_documents( documents=document )
    
    # Embeddings
    embedding_model = OpenAIEmbeddings(model='text-embedding-ada-002')

    # Supabase Credentials registration
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SECRET_KEY")
    
    client = create_client(supabase_url, supabase_key)

    # pgvector Credentials registration
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "postgres")

    if not all([DB_USER, DB_PASSWORD, DB_HOST]):
        raise ValueError(
            "Faltan variables de base de datos en .env\n"
            "Requeridas: DB_USER, DB_PASSWORD, DB_HOST"
        )

    DATABASE_URL = f"postgresql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    #************************** a mejorar esta parte *************************#
    # DataBase creation
    try:
        sync_connection = psycopg.connect(DATABASE_URL)
        PostgresChatMessageHistory.create_tables(sync_connection, "Text_on_Ai")
        sync_connection.close()
    except Exception as e:
        print(f"⚠️ Nota sobre tabla: {e}")
    
    # Store to Vector DataBase
    vectorstore = SupabaseVectorStore.from_documents(
        documents=chunks,
        embedding=embedding_model,
        client=client,
        table_name="Text_on_Ai",
        query_name="query_Ai_Document",
    )
    #***************************************************************************#

    return None

Ingestion('Knowledge Base/Text on Ai.pdf')