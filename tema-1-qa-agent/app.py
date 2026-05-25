import gradio as gr
from agent import run_agent

agent_history = []


def chat(message, history):
    return run_agent(message, agent_history)


demo = gr.ChatInterface(
    fn=chat,
    title="QA Agent",
    description="Agent ReAct cu tools: calculator, datetime, currency, random_fact, web_search",
    examples=[
        "Cât fac 25 * 4?",
        "Câți lei fac 100 euro?",
        "Spune-mi un fapt interesant.",
    ],
)

if __name__ == "__main__":
    demo.launch()
