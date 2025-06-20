import json
import yaml
import streamlit as st
from openai import OpenAI

from prompts import system_prompt, validity_prompt, category_prompt, context_template
from utils import ProjectDataException

def initialize_session_state():
    if "openai_model" not in st.session_state:
        st.session_state["openai_model"] = "gpt-3.5-turbo"
    if "messages" not in st.session_state:
        st.session_state.messages = []


def get_dropdown_mappings():
    dropdown_mappings = {
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
    return dropdown_mappings


def display_chat_history():
    for message in st.session_state.messages:
        if message["role"] in ["user", "assistant"]:
            with st.chat_message(message["role"]):
                    st.markdown(message["content"])


def check_question_validity(client, prompt):
    response = client.chat.completions.create(
        model=st.session_state["openai_model"],
        messages=[
            {"role": "system",
             "content": validity_prompt},
            {"role": "user", "content": prompt},
        ],
    )
    response = json.loads(response.choices[0].message.content)
    return response["is_valid"], response["language"], response["message"]


def get_question_category(client, prompt):
    response = client.chat.completions.create(
        model=st.session_state["openai_model"],
        messages=[
            {"role": "system",
             "content": category_prompt},
            {"role": "user", "content": prompt},
        ],
    )
    response = json.loads(response.choices[0].message.content)
    return response["category"]


def generate_final_response(client, prompt, grade, project_name, project_key, project_phase, language, question_category):
    project_filename = "./project_data/{}.yml".format(project_key)
    try:
        with open(f"{project_filename}", "r", encoding="utf-8") as file:
            project_data = yaml.safe_load(file)
            project_driving_question = project_data.get("driving_question", "No driving question found.")
            phase_overview = project_data.get("phases", {}).get(project_phase.lower(), {}).get("summary", "No overview found.")
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
        supplemental_resources='No supplemental resources available.'  # TODO: Placeholder for supplemental resources
    )
    stream = client.chat.completions.create(
        model=st.session_state["openai_model"],
        messages=[
            {"role": "system", "content": f"{context}"},
            {"role": "user", "content": prompt},
        ],
        stream=True,
    )
    return st.write_stream(stream)


def main():
    st.title("Saksham Parents Guide Chat")
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    initialize_session_state()

    dropdown_mappings = get_dropdown_mappings()

    grade = st.selectbox("Select Grade", list(dropdown_mappings.keys()))
    project_options = dropdown_mappings.get(grade, {}).keys()
    project_name = st.selectbox("Select Project", project_options)
    project_key = dropdown_mappings[grade][project_name]["key"]
    project_phase = st.selectbox("Select Project Phase", ["Explore", "Learn", "Design", "Exhibit", "Reflect"])

    display_chat_history()

    if not grade or not project_name or not project_phase:
        st.error("Please select a grade, project, and project phase to start the chat.")
        return

    st.session_state.messages.append({"role": "system", "content": system_prompt})

    if prompt := st.chat_input("Hi! How can I help you?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        is_valid, langauge, message = check_question_validity(client, prompt)

        if not is_valid:
            st.error(message)
            st.session_state.messages.append({"role": "assistant", "content": message})
            st.stop()
        else:
            category_response = get_question_category(client, prompt)

            if 'unrelated' in category_response.lower():
                st.error("The question does not seem to be related to the project. "
                         "Please ask a relevant question or if you need help with something else, please contact the teacher.")
                st.stop()
            elif 'unknown' in category_response.lower():
                st.error("I'm unable to determine the answer to your question. Please rephrase your question or contact the teacher.")
                st.stop()
            elif 'other' in category_response.lower():
                st.warning("I'm not sure of my answer to this question. Proceed with caution.")

            response = generate_final_response(
                client=client,
                prompt=prompt,
                grade=grade,
                project_name=project_name,
                project_key=project_key,
                project_phase=project_phase,
                language=langauge,
                question_category=category_response
            )
            st.session_state.messages.append({"role": "assistant", "content": response})

main()