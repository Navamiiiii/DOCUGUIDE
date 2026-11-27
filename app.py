"""Launch the local DocuGuide chatbot interface."""

import gradio as gr
from pathlib import Path

from chatbot import answer_question
from data_manager import list_services
from nlp import parse_query


def respond(message, history, selected_service):
    mentioned_service = parse_query(message).service_name
    active_service = mentioned_service or selected_service
    answer = answer_question(message, history, context_service=active_service)
    return answer, active_service


def main():
    services = list_services()
    names = ", ".join(item["service_name"] for item in services)
    print(f"Starting DocuGuide from: {Path(__file__).resolve().parent}")
    selected_service = gr.State(value=None)
    demo = gr.ChatInterface(
        fn=respond,
        additional_inputs=[selected_service],
        additional_outputs=[selected_service],
        title="DocuGuide",
        description=(
            "Ask about Karnataka Seva Sindhu certificate services. "
            f"Current catalogue: {names}. NLP recognizes services, documents, and question types; "
            "answers are drawn from the local JSON dataset."
        ),
        examples=[
            ["What documents are needed for an income certificate?", None],
            ["How long does a residence certificate take?", None],
            ["What is the fee for a caste certificate?", None],
            ["How do I apply for a birth certificate?", None],
        ],
    )
    demo.launch()


if __name__ == "__main__":
    main()
