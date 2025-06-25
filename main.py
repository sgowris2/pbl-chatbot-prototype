import base64
import json

import streamlit as st
import yaml
from openai import OpenAI
from streamlit.components.v1 import html
from streamlit_float import float_css_helper, float_parent, float_init

from prompts import system_prompt, validity_prompt, category_prompt, context_template, final_prompt_template
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

def display_messages(latest_only=False):

    if len(st.session_state.messages) < 2:

        def get_base64_image(image_path):
            with open(image_path, "rb") as img_file:
                return base64.b64encode(img_file.read()).decode()
        image_data = get_base64_image("static/ai_robot.jpg")

        st.markdown(f"""
            <div style='text-align: center; display: flex; flex-direction: column; justify-content: center; align-items: center;'>
                <img src="data:image/png;base64,{image_data}" width="300" style="border-radius: 15px; border: 0px solid gray; max-width: 100%; height: auto;" />
                <h3 style='color: #1f4760;'>Hi! I'm Akshu.</h3>
                <p style='font-size: 18px; color: #555;'>I'm here to help you with your project!</p>
            </div>
        """, unsafe_allow_html=True)
        return

    avatars = {"assistant": "💡", "user": "❓", "error": "⚠️"}

    messages = [st.session_state.messages[-1]] if latest_only else st.session_state.messages

    for idx, message in enumerate(messages):
        if message.get("error", False):  # Check if the message is an error
            with st.chat_message("assistant", avatar=avatars["error"]):
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
            with st.chat_message(message["role"], avatar=avatars[message["role"]]):
                st.markdown(message["content"])

        if not latest_only:
            scroll_to_bottom(anchor_id=f"scroll-anchor-{idx}")
        else:
            scroll_to_bottom(anchor_id=f'scroll-anchor-{len(st.session_state.messages) - 1}')

def display_chat_history():
    display_messages()

def display_latest_message():
    display_messages(latest_only=True)

def check_question_validity(client, prompt, context, past_messages):
    response = client.chat.completions.create(
        model=st.session_state["openai_model"],
        messages=[
            {"role": "system", "content": validity_prompt},
            {"role": "system", "content": context},
            {"role": "system", "content": "You have access to the following past messages for context: " + json.dumps(
                past_messages) if past_messages else ""},
            {"role": "user", "content": prompt}
        ],
    )
    result = json.loads(response.choices[0].message.content)
    if DEBUG:
        print(result)
    return result['prompt'], result["is_valid"], result["language"], result["message"], result["is_default"]


def get_question_category(client, prompt, context):
    response = client.chat.completions.create(
        model=st.session_state["openai_model"],
        messages=[
            {"role": "system", "content": category_prompt},
            {"role": "system", "content": context},
            {"role": "user", "content": prompt},
        ],
    )
    if DEBUG:
        print(response.choices[0].message.content)
    return json.loads(response.choices[0].message.content)["category"]


def generate_final_response(client, prompt, grade, project_name, project_key, project_phase, language,
                            question_category, project_driving_question, phase_overview, phase_instructions):

    context_prompt = final_prompt_template.format(
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
            {"role": "system", "content": context_prompt},
            {"role": "user", "content": prompt},
        ],
        stream=False,
    )
    if DEBUG:
        print(response.choices[0].message.content)
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


def render_project_guide(project_key, phase=None):
    import streamlit as st
    import yaml

    project_filename = f"./project_data/{project_key}.yml"
    with open(project_filename, "r", encoding="utf-8") as file:
        data = yaml.safe_load(file)
    phases = data.get("phases", {})
    if phase is not None:
        phases = {phase.lower(): phases.get(phase.lower(), {})}

    st.markdown(f"# 🏗️ {data.get('title', 'Project Title')}")
    st.markdown(f"### ❓ Driving Question\n> {data.get('driving_question', '')}")

    # --- Create a tab for each phase ---
    tab_labels = [details.get("name", key.title()) for key, details in phases.items()]
    tabs = st.tabs(tab_labels)

    # --- Render each tab dynamically ---
    for (key, details), tab in zip(phases.items(), tabs):
        with tab:
            st.markdown(f"### ⏱️ Duration: `{details.get('duration', 'N/A')}`")

            if summary := details.get("summary"):
                with st.expander("📝 Summary", expanded=True):
                    st.markdown(f"<div style='font-size: 1.1em; line-height: 1.6;'>{summary}</div>",
                                unsafe_allow_html=True)

            if hook := details.get("story_hook"):
                with st.expander("🎣 Story Hook"):
                    if isinstance(hook, list):
                        for item in hook:
                            if isinstance(item, dict):
                                for k, v in item.items():
                                    st.markdown(f"**{k.capitalize()}:** {v}")
                            else:
                                st.markdown(f"- {item}")

            if activities := details.get("activities"):
                with st.expander("🎯 Activities"):
                    for act in activities:
                        st.markdown(f"#### 🔹 {act.get('name')}")
                        st.markdown(f"{act.get('description', '')}")
                        if steps := act.get("steps"):
                            st.markdown("**👣 Steps:**")
                            for step in steps:
                                st.markdown(f"- {step}")
                        if simplifications := act.get("simplifications"):
                            st.markdown("**🧩 Simplifications:**")
                            for s in simplifications:
                                st.markdown(f"- {s}")
                        if extensions := act.get("extensions"):
                            if extensions:
                                st.markdown("**🚀 Extensions:**")
                                for e in extensions:
                                    st.markdown(f"- {e}")
                        st.markdown("---")

            section_info = [
                ("🧰 Tools & Materials", "tools_materials"),
                ("🎨 Student Outputs", "student_output"),
                ("💬 Potential Questions", "potential_questions"),
                ("🧑‍🏫 Facilitation Notes", "facilitation_notes"),
                ("📋 General Guidelines", "general_guidelines"),
            ]

            for section_title, field_key in section_info:
                items = details.get(field_key)
                if items:
                    with st.expander(section_title):
                        for item in items:
                            st.markdown(f"- {item}")


def main(debug=False):


    float_init(theme=True, include_unstable_primary=False)
    st.set_page_config(layout="wide")
    initialize_session_state()
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

    # Layout columns
    col1, col2 = st.columns([2, 1], gap="large")

    with col1:
        with st.container(border=False):
            st.title("SakshamProjects Guide Resources")
            dropdown_mappings = get_dropdown_mappings()
            subcol_1, subcol_2, subcol_3 = st.columns([1, 1, 1], gap="small")
            with subcol_1:
                grade = st.selectbox("Select Grade", list(dropdown_mappings.keys()))
            with subcol_2:
                project_options = dropdown_mappings.get(grade, {}).keys()
                project_name = st.selectbox("Select Project", project_options)
            with subcol_3:
                project_key = dropdown_mappings[grade][project_name]["key"]
                project_phase = st.selectbox("Select Project Phase",
                                             ["Explore", "Learn", "Design", "Exhibit", "Reflect"])

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

            context_prompt = context_template.format(
                grade=grade,
                project_name=project_name,
                project_phase=project_phase,
                project_driving_question=project_driving_question,
                phase_overview=phase_overview,
                phase_instructions=phase_instructions,
                supplemental_resources='No supplemental resources available.'  # TODO: Placeholder
            )

            with st.container(border=False):
                custom_css = float_css_helper(
                    height="60%",  # Set a fixed height
                    width="60%",
                    overflow_y="auto",  # Enable vertical scrolling
                    padding="3rem",
                    border="0.5px solid #ccc",
                )
                float_parent(css=custom_css)
                # if button_pressed:
                render_project_guide(project_key, phase=project_phase)

    with (col2):
        with st.container():
            if not grade or not project_name or not project_phase:
                st.error("Please select a grade, project, and project phase to start the chat.")
                return
            st.session_state.messages.append({"role": "system", "content": system_prompt})
            prompt = st.chat_input("Ask me anything about your project!", key='chat_input')
            button_css = float_css_helper(bottom="2rem",
                                          height="10%",
                                          width="30%",
                                          padding="2rem 0rem",
                                          overflow_y="auto",
                                          transition=0)
            float_parent(css=button_css)

        with st.container(border=False):
            custom_css = float_css_helper(
                height="70%",  # Set a fixed height
                width="30%",
                overflow_y="auto",  # Enable vertical scrolling
                padding="1rem",
                border="0.5px solid #ccc",
                background="#ffffff",
            )
            float_parent(css=custom_css)

            display_chat_history()

            if prompt:
                st.session_state.messages.append({"role": "user", "content": prompt})
                display_latest_message()

                rewritten_prompt, is_valid, language, message, is_default = \
                    check_question_validity(client, prompt, context_prompt, st.session_state.messages[-10:])
                if not is_valid:
                    st.session_state.messages.append({"role": "assistant", "error": True, "content": message})
                    display_latest_message()
                    st.stop()
                else:
                    if is_default:
                        st.session_state.messages.append({"role": "assistant", "content": message})
                        display_latest_message()
                        st.stop()
                    else:
                        category_response = get_question_category(client, rewritten_prompt, context_prompt)
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
                            prompt=rewritten_prompt,
                            grade=grade,
                            project_name=project_name,
                            project_key=project_key,
                            project_phase=project_phase,
                            language=language,
                            question_category=category_response,
                            project_driving_question=project_driving_question,
                            phase_overview=phase_overview,
                            phase_instructions=phase_instructions
                        )
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

DEBUG = True
main()
