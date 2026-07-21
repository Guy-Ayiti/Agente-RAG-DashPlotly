import os
import uuid
import time
import asyncio
import requests
from pathlib import Path
from dotenv import load_dotenv

import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc

import inngest

WELCOME_MESSAGE = """ Hola. Soy un asistente para el análisis del PDF que decidas subir.

Puedo responder preguntas sobre:
- 📁 El contenido del PDF
- ✏️ La existencia o no de algún concepto en el PDF
- 📋 El número de párrafos
- 👤 El autor del PDF si es que viene mencionado

**¿Qué te gustaría saber?**""" 


# ============================================
# Setup
# ============================================
load_dotenv()

def get_inngest_client() -> inngest.Inngest:
    return inngest.Inngest(app_id="rag_app", is_production=False)

def save_uploaded_pdf(contents, filename) -> Path:
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    file_path = uploads_dir / filename
    # contents is base64 encoded string from dcc.Upload
    import base64
    content_string = contents.split(",")[1]
    file_bytes = base64.b64decode(content_string)
    file_path.write_bytes(file_bytes)
    return file_path

async def send_rag_ingest_event(pdf_path: Path) -> None:
    client = get_inngest_client()
    await client.send(
        inngest.Event(
            name="rag/ingest_pdf",
            data={
                "pdf_path": str(pdf_path.resolve()),
                "source_id": pdf_path.name,
            },
        )
    )

async def send_rag_query_event(question: str, top_k: int) -> str:
    client = get_inngest_client()
    result = await client.send(
        inngest.Event(
            name="rag/query_pdf_ai",
            data={
                "question": question,
                "top_k": top_k,
            },
        )
    )
    return result[0]

def _inngest_api_base() -> str:
    return os.getenv("INNGEST_API_BASE", "http://127.0.0.1:8288/v1")

def fetch_runs(event_id: str) -> list[dict]:
    url = f"{_inngest_api_base()}/events/{event_id}/runs"
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    return data.get("data", [])

def wait_for_run_output(event_id: str, timeout_s: float = 120.0, poll_interval_s: float = 0.5) -> dict:
    start = time.time()
    last_status = None
    while True:
        runs = fetch_runs(event_id)
        if runs:
            run = runs[0]
            status = run.get("status")
            last_status = status or last_status
            if status in ("Completed", "Succeeded", "Success", "Finished"):
                return run.get("output") or {}
            if status in ("Failed", "Cancelled"):
                raise RuntimeError(f"Function run {status}")
        if time.time() - start > timeout_s:
            raise TimeoutError(f"Timed out waiting for run output (last status: {last_status})")
        time.sleep(poll_interval_s)

# ============================================
#              Dash App Config
# ============================================
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Agente conversacional con RAG"

#app.layout = dbc.Container(fluid=True, children=[
#    html.H1("📄 Seleccionar el PDF a subir :"),
#    dcc.Upload(
#        id="upload-pdf",
#        children=html.Div(["Seleccionar el pdf"]),
#        multiple=False,
#        style={
#            "width": "100%", "height": "60px", "lineHeight": "60px",
#            "borderWidth": "1px", "borderStyle": "dashed",
#            "borderRadius": "5px", "textAlign": "center"
#        }
#    ),
#    html.Div(id="upload-status", className="mt-3"),
#    html.Hr(),
#    html.H2("Preguntas acerca del PDF cargado :"),
#    dbc.Input(id="question-input", placeholder="Ingresa tu Pregunta :", type="text"),
#    #dbc.Input(id="topk-input", placeholder="Top K chunks", type="number", min=1, max=20, value=5),
#    dbc.Button("Ask", id="ask-btn", color="primary", className="mt-2"),
#    html.Div(id="answer-output", className="mt-4")
#])

app.layout = dbc.Container(fluid=True, children=[
    dbc.Row([
        # Sidebar
        dbc.Col(width=3, children=[
            html.Br(),
            html.Br(),

            html.Div([
                html.Img(src="assets/robot.png", style={"width": "30%"})
                ], style={"display": "flex", "justifyContent": "center", "alignItems": "center"}
            ),

            html.Br(),    
            html.H2("📌 Menu", style={"fontSize": "20px", 'textAlign': 'center'}),
            html.Hr(),

            html.Div([
                dcc.Upload( 
                    id="upload-pdf",
                    children=dbc.Button("Seleccionar el pdf", style={"backgroundColor":"#F1901B", 'border':'none'}),
                    multiple=False
                )
            ], style={"display": "flex","justifyContent": "center", "alignItems": "center"}),

            html.Div(id="upload-status", className="mt-3"),
            html.Br(),
            html.Div("Este agente utiliza openAI y LLama-index " \
                     "para contestar preguntas en lenguaje natural " \
                     "sobre un PDF que carga el usuario.", style={"borderRadius":"10px",
                                                                 "padding": "10px",
                                                                 "color":"steelblue", #"fontWeight": "bold", 
                                                                 "backgroundColor":"#CEDAE9"}),
            html.Br(),
            html.Div(id="thread-id", style={"fontFamily": "monospace", "backgroundColor": "#f8f9fa", "padding": "5px"}),
        ], style={'backgroundColor':'#EAECF0'}),

        # Main Chat Area
        dbc.Col(width=9, children=[
            html.Br(),
            html.Br(),
            html.Br(),
            dbc.Row([
                html.H1("🔍 Conversación con Agente", style={"fontSize": "20px", 'textAlign': 'center'}),
                #html.Hr(),
                html.Div(id="chat-history", style={"height": "400px", "overflowY": "scroll", "border": "none", "padding": "10px"}),
            ], style={'marginLeft':'50px', 'marginRight':'20px'}),
            html.Br(),
            html.Br(),
            html.Br(),
            dbc.Row([
                dbc.Input(id="user-input", placeholder="Escribe tu pregunta aquí...", type="text", style={"backgroundColor":'#EAECF0'}),
                #dbc.Button("Enviar", id="send-btn", style={"backgroundColor":"darkorange", "border": "none"}, className="mt-2")
            ], style={'marginLeft':'50px', 'marginRight':'20px'}),
        ])
    ])
])


#============================================
#                 Callbacks
#============================================

@app.callback(
    Output("upload-status", "children"),
    Input("upload-pdf", "contents"),
    State("upload-pdf", "filename"),
    prevent_initial_call=True
)
def handle_upload(contents, filename):
    if contents and filename:
        try:
            path = save_uploaded_pdf(contents, filename)
            asyncio.run(send_rag_ingest_event(path))
            return dbc.Alert(f"Triggered ingestion for: {path.name}", color="success")
        except Exception as e:
            return dbc.Alert(f"Error uploading: {str(e)}", color="danger")
    return ""

@app.callback(
    Output("chat-history", "children"),
    Output("user-input", "value"),
    #Output("answer-output", "children"),
    #Input("send-btn", "n_clicks"),
    Input("user-input", "n_submit"),
    State("user-input", "value"),
    State("chat-history", "children"),
    #State("topk-input", "value"),
    #prevent_initial_call=True
)
def update_chat(n_clicks, question, history): #, top_k):
    if not history:
        history = [html.Div([html.B("Agente 🤖 : "), html.Span(WELCOME_MESSAGE, style={'whiteSpace': 'pre-wrap'})], 
                            style={'backgroundColor': '#E9EBEF',
                                   'marginTop':'20px', 'marginDown':'20px'})]

    #if not question.strip():
    #    return dbc.Alert("Favor de hacer su pregunta.", color="warning")
    
    if question:
        history.append(html.Div([html.B("Usuario 😊 : "), html.Span(question)],
                                style={'backgroundColor': '#CDE1BD',
                                   'marginTop':'20px', 'marginDown':'20px'}))

        try:
            event_id = asyncio.run(send_rag_query_event(question.strip(), 5)) #int(top_k)))
            output = wait_for_run_output(event_id)
            answer = output.get("answer", "")
            sources = output.get("sources", [])
            #children = [html.H4("Answer"), html.P(answer or "(No answer)")]
            if sources:
                history.append(html.Div([html.B("Agente 🤖 : "), html.Span(answer)], 
                                        style={'backgroundColor': '#E9EBEF', 
                                               'marginTop':'20px', 'marginDown':'20px'}))
                #children.append(html.H6("Sources"))
                #children.extend([html.Li(s) for s in sources])
            #return history #children
        except Exception as e:
            return dbc.Alert(f"Error: {str(e)}", color="danger")
    return history, ""

#============================================
#                      Run
#============================================
if __name__ == "__main__":
    app.run(debug=True)


























