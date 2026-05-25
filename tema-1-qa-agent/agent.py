from dotenv import load_dotenv
import os
import json
import datetime
from google import genai

from tools import ToolWrapper
from prompts.registry import PromptRegistry

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
registry = PromptRegistry("prompts")
MAX_ITERATIONS = 10


def build_tools_description() -> str:
    lines = []
    for tool in ToolWrapper.catalog():
        props = tool["params_schema"].get("properties", {})
        required = tool["params_schema"].get("required", [])
        params = ", ".join(
            f"{k}{'*' if k in required else ''}: {v.get('type', 'any')}"
            for k, v in props.items()
        )
        lines.append(f"- {tool['name']}({params}): {tool['description']}")
    return "\n".join(lines)


def ask(history: list) -> str:
    response = client.models.generate_content(
        model="gemini-2.0-flash-lite", contents=history
    )
    return response.text


def run_agent(question: str, history: list) -> str:
    if not history:
        system_prompt = registry.render(
            "planner",
            current_date=datetime.date.today().isoformat(),
            tools_description=build_tools_description(),
        )
        history.extend(
            [
                {"role": "user", "parts": [{"text": system_prompt}]},
                {
                    "role": "model",
                    "parts": [
                        {
                            "text": "Am înțeles. Sunt gata să rezolv task-uri folosind tools."
                        }
                    ],
                },
            ]
        )

    history.append({"role": "user", "parts": [{"text": question}]})

    for i in range(MAX_ITERATIONS):
        response_text = ask(history)
        history.append({"role": "model", "parts": [{"text": response_text}]})
        print(f"\n[Step {i + 1}] {response_text}")

        try:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start == -1:
                raise ValueError("Nu am găsit JSON în răspuns.")
            data = json.loads(response_text[start:end])
        except Exception as e:
            history.append(
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": f"Răspunsul tău nu e JSON valid: {e}. Încearcă din nou."
                        }
                    ],
                }
            )
            continue

        if "final_answer" in data:
            return data["final_answer"]

        if "tool" in data:
            tool_name = data["tool"]
            tool_args = data.get("args", {})
            observation = ToolWrapper.call(tool_name, tool_args)
            print(f"[Tool: {tool_name}] → {observation}")
            history.append(
                {"role": "user", "parts": [{"text": f"Observe: {observation}"}]}
            )
            continue

        history.append(
            {
                "role": "user",
                "parts": [
                    {
                        "text": "Răspunsul nu conține 'tool' sau 'final_answer'. Urmează formatul."
                    }
                ],
            }
        )

    return "Nu am găsit răspunsul în numărul maxim de iterații."


if __name__ == "__main__":
    history = []
    print("QA Agent pornit. Scrie 'exit' pentru a ieși.\n")
    while True:
        question = input("Tu: ")
        if question.lower() == "exit":
            break
        answer = run_agent(question, history)
        print(f"\nAgent: {answer}\n")
