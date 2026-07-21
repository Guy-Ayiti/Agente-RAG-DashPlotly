import os
import uuid
import time
import base64
import asyncio
from pathlib import Path
from dotenv import load_dotenv

import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc


# import pinecone
from pinecone import Pinecone, ServerlessSpec

# import langchain
from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from Ingestion import IngestData
from Retrieval import RetrieveData
from openai import OpenAI

load_dotenv()

# initialize the OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


WELCOME_MESSAGE = """ Hola. Soy un asistente para el análisis del PDF que decidas subir.

Puedo responder preguntas sobre:
- 📁 El contenido del PDF
- ✏️ La existencia o no de algún concepto en el PDF
- 📋 El número de párrafos
- 👤 El autor del PDF si es que viene mencionado

**¿Qué te gustaría saber?**""" 

#============================================#
#                 Initializing               #
#============================================#

# initialize pinecone database
pinecone = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))

# initialize pinecone database
index_name = os.environ.get("PINECONE_INDEX_NAME")
index = pinecone.Index(index_name)

# initialize embeddings model + vector store
embeddings = OpenAIEmbeddings(model="text-embedding-3-large",
                              api_key=os.environ.get("OPENAI_API_KEY"),
                              dimensions=1024)
vector_store = PineconeVectorStore(index=index, embedding=embeddings)



TEXTO_BIENVENIDA = "Este agente utiliza ", html.B('openAI')," y ", html.B('Langchain')," " \
                "para contestar preguntas en lenguaje natural " \
                "sobre un PDF que carga el usuario " \
                "a la base de datos vectorial ", html.B('Pinecone'),"."
#============================================#
#              Dash App Config               #
#============================================#
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Agente conversacional con RAG"

app.layout = dbc.Container(fluid=True, children=[
    dbc.Row([
        # Sidebar
        dbc.Col(width=3, children=[
            html.Br(),
            html.Br(),

            html.Div( [ html.Img(src="assets/robot-head.png", style={"width": "10%"})], 
                                 style={"display": "flex", 
                                        "justifyContent": "center", 
                                        "alignItems": "center"}),
            html.Br(),                                        
            html.H1("Agente RAG", style={"fontSize": "20px", 'textAlign': 'center', "fontWeight": "bold"}),
            html.Br(),
            html.Hr(),
            html.Br(),

            html.Div(TEXTO_BIENVENIDA, style={"borderRadius":"10px",
                                              "padding": "10px",
                                              "color":"#0043DA", #"fontWeight": "bold", 
                                              "backgroundColor":"#CEDAE9"}),
            html.Br(),
            html.Br(),     
            html.H2("📌 Menu", style={"fontSize": "20px", 'textAlign': 'center'}),
            html.Hr(),
            html.Br(),

            html.Div([
                dcc.Upload( 
                    id="upload-pdf",
                    children=dbc.Button("Seleccionar el pdf", style={"backgroundColor":"#F1901B", 'border':'none'}),
                    multiple=False
                )
            ], style={"display": "flex","justifyContent": "center", "alignItems": "center"}),

            html.Div(id="upload-status", className="mt-3"),
            html.Br(),
            html.Br(),
        ], style={'backgroundColor':'#EAECF0'}),

        # Main Chat Area
        dbc.Col(width=9, children=[
            html.Br(),
            html.Br(),
            html.Br(),
            dbc.Row([
                dbc.Col(width=3, children=[
                    html.Div([ html.Img(src="assets/robot.png", style={"width": "30%"})], 
                               style={"display": "flex", "justifyContent": "left", "alignItems": "left"}),
                ]),
                dbc.Col([
                    html.H1("Conversación con Agente🔻", 
                            style={"fontSize": "20px", "color":"steelblue", 
                                   'textAlign': 'left', "marginTop": "60px", "marginLeft": "50px"}),
                ]),
                #html.Hr(),
            ], style={'marginLeft':'50px', 'marginRight':'50px'}),

            dbc.Row([
                html.Div(id="chat-history", 
                         style={"height": "400px", "overflowY": "scroll", "border": "none"}),
            ], style={'marginLeft':'50px', 'marginRight':'50px'}),

            html.Br(),
            html.Br(),
            html.Br(),
            dbc.Row([
                dbc.Input(id="user-input", placeholder="Escribe tu pregunta aquí...", type="text", style={"backgroundColor":'#EAECF0'}),
                #dbc.Button("Enviar", id="send-btn", style={"backgroundColor":"darkorange", "border": "none"}, className="mt-2")
            ], style={'marginLeft':'50px', 'marginRight':'50px'}),
        ])
    ]) # , style={"border": "2px solid black","padding": "10px", "borderWidth": "30px"}
])


#============================================#
#                 Callbacks                  #
#============================================#

@app.callback(
    Output("upload-status", "children"),
    Input("upload-pdf", "contents"),
    State("upload-pdf", "filename"),
    prevent_initial_call=True
)
def handle_upload(contents, filename):
    if contents and filename:
        try:
            # Decode the uploaded file into raw bytes
            content_string = contents.split(",")[1]
            file_bytes = base64.b64decode(content_string)   # is the binary content of the PDF

            # Save to local "Documents" directory
            uploads_dir = Path("Documents")
            uploads_dir.mkdir(parents=True, exist_ok=True)
            file_path = uploads_dir / filename
            file_path.write_bytes(file_bytes)

            # Call ingestion function to push embeddings to Pinecone
            #IngestData(file_bytes) # Pass the raw PDF bytes directly to IngestData
            IngestData(str(file_path))

            return dbc.Alert(f"✅ PDF '{filename}' ingested into Pinecone.", color="success", style={"fontSize": "12px",'marginLeft':'50px', 'marginRight':'50px'})
        except Exception as e:
            return dbc.Alert(f"❌ Error during ingestion: {str(e)}", color="danger", style={"fontSize": "12px",'marginLeft':'50px', 'marginRight':'50px'})
    return dbc.Alert("No file uploaded.", color="warning", style={"fontSize": "12px",'marginLeft':'50px', 'marginRight':'50px'})

@app.callback(
    Output("chat-history", "children"),
    Output("user-input", "value"),     #Output("answer-output", "children"),
                                       #Input("send-btn", "n_clicks"),
    Input("user-input", "n_submit"),
    State("user-input", "value"),
    State("chat-history", "children"),
                                       #State("topk-input", "value"),
    #prevent_initial_call=True
)
def update_chat(n_clicks, question, history): #, top_k):
    if not history:
        history = [html.Div([html.B("⚫ Agente : "), html.Span(WELCOME_MESSAGE, style={'whiteSpace': 'pre-wrap'})], 
                            style={'backgroundColor': '#E9EBEF',
                                   'marginTop':'20px', 'marginDown':'20px', 
                                   "padding": "10px", "borderRadius":"10px"})]

    #if not question.strip():
    #    return dbc.Alert("Favor de hacer su pregunta.", color="warning")
    
    if question:
        history.append(html.Div([html.B("🟢 Usuario : "), html.Span(question)],
                                style={'backgroundColor': '#CDE1BD',
                                   'marginTop':'20px', 'marginDown':'20px',
                                   "padding": "10px", "borderRadius":"10px"}))

        try:
            # 🔎 Retrieve context from Pinecone
            results = RetrieveData(question)   # can be adapted to directly receive the question
            context_text = "\n".join([doc.page_content for doc in results])

            # Build system prompt with context
            system_prompt = f"""Eres un asistente para responder preguntas sobre PDFs.
            Usa el siguiente contexto para contestar de forma concisa (máximo 3 frases).
            Si no sabes la respuesta, avisar de que no lo sabes.
            Contexto:{context_text}"""


            # Call OpenAI chat completion with system + user messages
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ],
                temperature=1
            )
            answer = response.choices[0].message.content

            # Add assistant response
            history.append(html.Div([html.B("⚫ Agente : "), html.Span(answer)],
                                    style={'backgroundColor': '#E9EBEF',
                                           'marginTop':'20px', "padding": "10px", "borderRadius":"10px"}))
        except Exception as e:
            history.append(html.Div([html.B("⚠️ Error : "), html.Span(str(e))],
                                    style={'backgroundColor': '#FFCCCC',
                                           'marginTop':'20px', "padding": "10px", "borderRadius":"10px"}))
    # Clear the input box after submission
    return history, ""

#============================================
#                      Run
#============================================
if __name__ == "__main__":
    app.run(debug=True)

















