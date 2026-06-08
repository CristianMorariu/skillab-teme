import os

import gradio as gr
from dotenv import load_dotenv

from agent import QAAgent
from pipeline import ExtractionPipeline
from seed import run as seed_db

load_dotenv()

seed_db()

pipeline = ExtractionPipeline()
agent = QAAgent(provider=os.getenv("LLM_PROVIDER", "openrouter"), system_prompt="")

CSS = """
#sidebar {
    background: #16213e;
    border-radius: 12px;
    padding: 24px 16px;
    min-height: 80vh;
}
#sidebar h1 { color: #e94560; font-size: 1.4em; margin-bottom: 4px; }
#sidebar p  { color: #a8a8b3; font-size: 0.85em; margin-top: 0; }
#send-btn { width: 100%; margin-top: 8px; }
footer { display: none !important; }
"""


def ingest_document(file, doc_type):
    if file is None:
        return "Te rog încarcă un fișier."
    try:
        result = pipeline.process(file, doc_type)
        if result is None:
            return "Document salvat pentru RAG.\n(Tip CSV — fără extracție structurată)"
        numar = getattr(result, "numar", "N/A")
        total = getattr(result, "total", getattr(result, "valoare", "N/A"))
        return f"Procesat cu succes!\nNumăr: {numar}\nTotal: {total}"
    except Exception as e:
        return f"Eroare: {e}"


def chat(message, history):
    if not message.strip():
        yield "", history
        return
    history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": "Se procesează..."},
    ]
    yield "", history
    answer = agent.run_agent(message)
    history[-1] = {"role": "assistant", "content": answer}
    yield "", history


with gr.Blocks(css=CSS, title="Document Analyst") as demo:
    with gr.Row(equal_height=True):

        # ── Sidebar ──────────────────────────────────────────
        with gr.Column(scale=1, elem_id="sidebar"):
            gr.HTML("<h1>Document Analyst</h1><p>RAG Agent · Tema 2</p>")
            gr.Markdown("---")
            gr.Markdown("**Încarcă document**")
            file_input = gr.File(label="TXT · PDF · DOCX", file_count="single")
            doc_type = gr.Dropdown(
                choices=["factura", "contract", "csv"],
                value="factura",
                label="Tip document",
            )
            ingest_btn = gr.Button("Procesează", variant="primary")
            ingest_status = gr.Textbox(
                label="Status", lines=3, interactive=False, show_label=True
            )

        # ── Chat ─────────────────────────────────────────────
        with gr.Column(scale=2):
            gr.Markdown("### Chat")
            chatbot = gr.Chatbot(height=520, show_label=False)
            msg_input = gr.Textbox(
                placeholder="Întreabă ceva despre documentele încărcate...",
                label="",
                lines=2,
                show_label=False,
            )
            send_btn = gr.Button("Trimite", variant="primary", elem_id="send-btn")

    ingest_btn.click(ingest_document, inputs=[file_input, doc_type], outputs=ingest_status)
    send_btn.click(chat, inputs=[msg_input, chatbot], outputs=[msg_input, chatbot])
    msg_input.submit(chat, inputs=[msg_input, chatbot], outputs=[msg_input, chatbot])

if __name__ == "__main__":
    demo.launch()
