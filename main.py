import json
import time

import streamlit as st
from streamlit.components.v1 import html
import yaml
from openai import OpenAI
from streamlit_float import float_css_helper, float_parent, float_init

from prompts import system_prompt, validity_prompt, category_prompt, context_template
from utils import ProjectDataException


def initialize_session_state():
    if "openai_model" not in st.session_state:
        st.session_state["openai_model"] = "gpt-3.5-turbo"
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "show_chat" not in st.session_state:
        st.session_state["show_chat"] = True  # toggle for collapsible chat panel


def get_dropdown_mappings():
    return {
        "Grade 5": {
            "Heat Resistant House": {"key": "heat_resistant_house"},
            "Community Park": {"key": "community_park"},
        },
        "Grade 6": {
            "News Bulletin": {"key": "news_bulletin"},
            "Healthy Snack Food": {"key": "healthy_snack_food"},
        },
        "Grade 7": {
            "Healthy, Hyperlocal Restaurant": {"key": "healthy_hyperlocal_restaurant"},
        },
        "Grade 8": {
            "Are We Cleaning Or Polluting?": {"key": "are_we_cleaning_or_polluting"},
            "Carbon Footprint": {"key": "carbon_footprint"}
        },
    }


def display_chat_history():
    for idx, message in enumerate(st.session_state.messages):
        if message.get("error", False):  # Check if the message is an error
            with st.chat_message("assistant"):
                st.markdown(
                    f"""
                    <div style="background-color: #ffe6e6; padding: 10px; border-radius: 5px; border: 1px solid #ffcccc;">
                        <p style="color: #cc0000; font-size: 16px; margin: 0;">
                            {message["content"]}
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        elif message["role"] in ["user", "assistant"]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        scroll_to_bottom(anchor_id=f"scroll-anchor-{idx}")


def display_latest_message():
    message = st.session_state.messages[-1] if st.session_state.messages else None
    if message.get("error", False):  # Check if the message is an error
        with st.chat_message("assistant"):
            st.markdown(
                f"""
                <div style="background-color: #ffe6e6; padding: 10px; border-radius: 5px; border: 1px solid #ffcccc;">
                    <p style="color: #cc0000; font-size: 16px; margin: 0;">
                        {message["content"]}
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
    elif message["role"] in ["user", "assistant"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    scroll_to_bottom(anchor_id=f'scroll-anchor-{len(st.session_state.messages) - 1}')


def check_question_validity(client, prompt):
    response = client.chat.completions.create(
        model=st.session_state["openai_model"],
        messages=[
            {"role": "system", "content": validity_prompt},
            {"role": "user", "content": prompt},
        ],
    )
    result = json.loads(response.choices[0].message.content)
    return result["is_valid"], result["language"], result["message"]


def get_question_category(client, prompt):
    response = client.chat.completions.create(
        model=st.session_state["openai_model"],
        messages=[
            {"role": "system", "content": category_prompt},
            {"role": "user", "content": prompt},
        ],
    )
    return json.loads(response.choices[0].message.content)["category"]


def generate_final_response(client, prompt, grade, project_name, project_key, project_phase, language,
                            question_category):
    project_filename = f"./project_data/{project_key}.yml"
    try:
        with open(project_filename, "r", encoding="utf-8") as file:
            project_data = yaml.safe_load(file)
            project_driving_question = project_data.get("driving_question", "No driving question found.")
            phase_overview = project_data.get("phases", {}).get(project_phase.lower(), {}).get("summary",
                                                                                               "No overview found.")
            phase_instructions = project_data.get("phases", {}).get(project_phase.lower(), {})
    except Exception as e:
        raise ProjectDataException(f"Error loading project data: {e}")

    context = context_template.format(
        grade=grade,
        project_name=project_name,
        project_phase=project_phase,
        category=question_category,
        language=language,
        project_driving_question=project_driving_question,
        phase_overview=phase_overview,
        phase_instructions=phase_instructions,
        supplemental_resources='No supplemental resources available.'  # TODO: Placeholder
    )

    response = client.chat.completions.create(
        model=st.session_state["openai_model"],
        messages=[
            {"role": "system", "content": context},
            {"role": "user", "content": prompt},
        ],
        stream=False,
    )
    return response.choices[0].message.content.strip()


def scroll_to_bottom(anchor_id="scroll-anchor"):
    html(
        f"""
        <div id="{anchor_id}"></div>
        <script>
            console.log("Scrolling to anchor: {anchor_id}");
            setTimeout(function() {{
                var anchor = document.getElementById("{anchor_id}");
                if (anchor) {{
                    anchor.scrollIntoView({{ behavior: 'smooth', block: 'end' }});
                }} else {{
                    console.error("Anchor not found: {anchor_id}");
                }}
            }}, 100);
        </script>
        """,
    )


def main():
    float_init(theme=True, include_unstable_primary=False)
    st.set_page_config(layout="wide")
    initialize_session_state()
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

    # Layout columns
    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        with st.container(border=False):
            st.title("Saksham Projects Saathi")
            # st.subheader("Project Guide and AI Assistant")
            dropdown_mappings = get_dropdown_mappings()
            subcol_1, subcol_2, subcol_3 = st.columns([1, 1, 1], gap="small")
            with subcol_1:
                grade = st.selectbox("Select Grade", list(dropdown_mappings.keys()))
            with subcol_2:
                project_options = dropdown_mappings.get(grade, {}).keys()
                project_name = st.selectbox("Select Project", project_options)
            with subcol_3:
                project_key = dropdown_mappings[grade][project_name]["key"]
                project_phase = st.selectbox("Select Project Phase", ["Explore", "Learn", "Design", "Exhibit", "Reflect"])
            st.button("Apply", key="apply_button")
            st.markdown("---")

            with st.container(border=False):
                custom_css = float_css_helper(
                    height="50%",  # Set a fixed height
                    width="45%",
                    overflow_y="auto",  # Enable vertical scrolling
                    padding="3rem",
                    border="1px solid #ccc",
                    background="#f9f9f9",
                )
                float_parent(css=custom_css)
                for i in range(0, 100):
                    st.markdown(i)

    with col2:

        with st.container():
            if not grade or not project_name or not project_phase:
                st.error("Please select a grade, project, and project phase to start the chat.")
                return
            st.session_state.messages.append({"role": "system", "content": system_prompt})
            prompt = st.chat_input("Hi! How can I help you?", key='chat_input')
            button_css = float_css_helper(bottom="2rem",
                                          height="10%",
                                          width="45%",
                                          padding="2rem 0rem",
                                          overflow_y="auto",
                                          transition=0)
            float_parent(css=button_css)

        with st.container(border=False):
            custom_css = float_css_helper(
                height="70%",  # Set a fixed height
                width="45%",
                overflow_y="auto",  # Enable vertical scrolling
                padding="1rem",
                border="1px solid #ccc",
                background="#f9f9f9",
            )
            float_parent(css=custom_css)

            display_chat_history()

            if prompt:
                st.session_state.messages.append({"role": "user", "content": prompt})
                display_latest_message()

                is_valid, language, message = check_question_validity(client, prompt)
                if not is_valid:
                    st.session_state.messages.append({"role": "assistant", "error": True, "content": message})
                    display_latest_message()
                    st.stop()
                else:
                    category_response = get_question_category(client, prompt)
                    if 'unrelated' in category_response.lower():
                        response = "The question does not seem to be related to the project. Please ask a relevant question or contact the online coach."
                        st.session_state.messages.append({"role": "assistant", "error": True, "content": response})
                        display_latest_message()
                        st.stop()
                    elif 'unknown' in category_response.lower():
                        response = "I'm unable to determine the answer to your question. Please rephrase."
                        st.session_state.messages.append({"role": "assistant", "error": True, "content": response})
                        display_latest_message()
                        st.stop()

                    elif 'other' in category_response.lower():
                        st.warning("I'm not too sure of my answer to this question. Here’s my best attempt...")

                    response = generate_final_response(
                        client=client,
                        prompt=prompt,
                        grade=grade,
                        project_name=project_name,
                        project_key=project_key,
                        project_phase=project_phase,
                        language=language,
                        question_category=category_response
                    )
                    # time.sleep(60)  # Simulate processing time
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    display_latest_message()

st.markdown(
    """
    <style>
    .st-emotion-cache-as33y7 {
        height: 0 !important; /* Set your desired height */
    }
    .st-emotion-cache-866kcp {
        height: 0 !important; /* Set your desired height */
    }
    ..st-emotion-cache-1s06nf2 {
        height: 0 !important; /* Set your desired height */
    }
    iframe[Attributes Style] {
        height: 0 !important; /* Set your desired height */
    }
    </style>
    """,
    unsafe_allow_html=True,
)

main()


