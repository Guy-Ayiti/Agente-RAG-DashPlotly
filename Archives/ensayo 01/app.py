import os
import uuid
from datetime import datetime

import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage

from before.agent_runner import build_app, run_agent
from demo.conversation_or_chat_history import (
    ensure_checkpointer_tables,
    get_checkpointer,
    get_schema_name,
)

#============================================
#                   Setup
#============================================
load_dotenv()
ensure_checkpointer_tables()
app_agent = build_app(get_checkpointer())

#============================================
#               Dash App Config
#============================================
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Agente RAG - Joseph Guy Evans Jr Hilaire"

WELCOME_MESSAGE = """¡Hola! 👋 Soy tu asistente para analizar datos de un PDF.
Puedo responder preguntas sobre:
- 📊 Resumen del contenido
- 🗺️ Preguntas especificas
- ⏱️ Indicación de Preguntas fuera de alcance
- 👥 Otras sugerencias ?
**¿Qué te gustaría saber?**"""

#============================================
#                    Layout
#============================================
app.layout = dbc.Container(fluid=True, children=[
    dbc.Row([
        # Sidebar
        dbc.Col(width=3, children=[
            html.H2("🚴 Menu"),
            html.Hr(),
            html.H4("💡 Ejemplos de preguntas:"),
            dbc.Button("¿Que contiene el documento?", id="ejemplo1", color="secondary", className="mb-2"),
            dbc.Button("", id="ejemplo2", color="secondary", className="mb-2"),
            dbc.Button("¿Cuál es la duración promedio?", id="ejemplo3", color="secondary", className="mb-2"),
            dbc.Button("¿Cuántos usuarios son subscribers?", id="ejemplo4", color="secondary", className="mb-2"),
            dbc.Button("Dame las 5 estaciones más usadas", id="ejemplo5", color="secondary", className="mb-2"),
            dbc.Button("¿En qué año hay más viajes?", id="ejemplo6", color="secondary", className="mb-2"),
            html.Hr(),
            html.H5("💬 Conversación actual"),
            html.Div(id="thread-id", style={"fontFamily": "monospace", "backgroundColor": "#f8f9fa", "padding": "5px"}),
        ]),
        # Main Chat Area
        dbc.Col(width=9, children=[
            html.H1("🚴 Conversacion con Agente", className="text-center"),
            html.Hr(),
            html.Div(id="chat-history", style={"height": "500px", "overflowY": "scroll", "border": "1px solid #ddd", "padding": "10px"}),
            dbc.Input(id="user-input", placeholder="Escribe tu pregunta aquí...", type="text"),
            dbc.Button("Enviar", id="send-btn", color="primary", className="mt-2"),
        ])
    ])
])

#============================================
#                  Callbacks
#============================================

# Initialize thread_id
@app.callback(
    Output("thread-id", "children"),
    Input("send-btn", "n_clicks"),
    State("thread-id", "children"),
    prevent_initial_call=True
)
def update_thread_id(n_clicks, current_id):
    if not current_id:
        return str(uuid.uuid4())
    return current_id

# Handle chat flow
@app.callback(
    Output("chat-history", "children"),
    Input("send-btn", "n_clicks"),
    State("user-input", "value"),
    State("chat-history", "children"),
    State("thread-id", "children"),
    prevent_initial_call=True
)
def update_chat(n_clicks, user_msg, history, thread_id):
    if not history:
        history = [html.Div([html.B("Assistant: "), html.Span(WELCOME_MESSAGE)])]

    if user_msg:
        # Add user message
        history.append(html.Div([html.B("User: "), html.Span(user_msg)]))

        try:
            respuesta = run_agent(app_agent, user_msg, thread_id)
            history.append(html.Div([html.B("Assistant: "), html.Span(respuesta)]))
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            history.append(html.Div([html.B("Assistant: "), html.Span(error_msg)]))

    return history


#========================================================#
#                      Aplicacion                        #
#========================================================#
if __name__ == "__main__":
    app.run(debug=True)

