import os
import sys
import uuid

import pandas as pd
import streamlit as st

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from vertical_farm.data import PLANTS
from vertical_farm.simulator import simulate_month, LEVELS, LEVEL_AREA, INPUT_LEVELS, level_inputs


def initialize_session_state():
    if "user_id" not in st.session_state:
        st.session_state.user_id = str(uuid.uuid4())
        st.session_state.month = 0
        st.session_state.monthly_op_costs = dict()
        st.session_state.budget = 1000.0
        st.session_state.farm_df = pd.DataFrame(columns=[
            "level", "plant", "day_planted", "age", "space", "status"
        ])
        st.session_state.market_prices = {"Tomato": 12, "Lettuce": 8}
        st.session_state.monthly_logs = {}


def render_sidebar():
    st.sidebar.header("Info Panel")
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"👤 **User:** `{st.session_state.user_id[-5:]}`")
    st.sidebar.markdown(f"🗓 **Month:** {st.session_state.month} / 12")
    st.sidebar.markdown(f"💰 **Cash:** ₹{st.session_state.budget:.2f}")
    st.sidebar.markdown("###")
    with st.sidebar:
        render_performance()
    with st.sidebar:
        with st.expander("₹ Market Prices"):
            st.table(pd.DataFrame.from_dict(st.session_state.market_prices, orient="index", columns=["₹/kg"]))

    if st.sidebar.button('ⓘ Factsheet', key="factsheet_button"):
        render_factsheet()


@st.dialog("ⓘ Factsheet", width="large")
def render_factsheet():
    data = [
        ["Lettuce", 1, "18–24", "50–70", 20, 12, 0.17, "<12°C slows growth; >30°C causes tip‑burn"],
        ["Spinach", 1, "16–22", "50–70", 20, 17, 0.25, "Long-day plant; excess light may bolt"],
        ["Kale", 2, "16–22", "50–70", 20, 17, 0.25, "Grows well leaf-by-leaf; cold tolerant"],
        ["Swiss Chard", 2, "18–24", "50–70", 20, 17, 0.25, "Continuous harvest possible"],
        ["Arugula", 1, "18–24", "50–70", 20, 12, 0.20, "Fast growing, ideal for cut harvests"],
        ["Basil", 1, "20–27", "50–70", 20, 17, 0.20, "Cold-sensitive; mold risk in high humidity"],
        ["Cilantro", 1, "18–22", "50–70", 20, 17, 0.20, "Bolts >27°C; sensitive to humidity spikes"],
        ["Microgreens", 0, "20–24", "60–80", 10, 17, 0.05, "Harvest in 1–2 weeks"],
        ["Tomato (cherry)", 3, "22–26", "60–80", 750, 25, 30, "Fruit set poor <18°C; heat reduces quality"],
        ["Cucumber", 2, "24–28", "70–90", 750, 25, 27, "Low humidity causes flower drop"],
        ["Strawberry", 4, "18–24", "60–80", 350, 17, 33, "Sensitive to pH/EC; day-neutral types preferred"],
        ["Bell Pepper", 3, "19–23", "60–80", 450, 20, 15, "Slow flowering <21°C; needs support"],
        ["Eggplant", 3, "21–26", "60–80", 500, 20, 20, "Compact varieties preferred for vertical growth"],
        ["Beans (bush)", 3, "20–28", "60–80", 400, 20, 18, "Needs support; EC ~2.0 ideal"],
    ]
    df = pd.DataFrame(data, columns=[
        "Crop", "Months to Maturity", "Temp (°C)", "Humidity (%)",
        "Water (mL/day)", "Light (DLI)", "Nutrients (g/day)", "Tolerances / Notes"
    ])
    st.table(df)


def render_performance(expanded=True):
    with st.expander("📊 Farm Performance", expanded=expanded):
        total_revenue = sum(
            sum(log["revenue"] for log in month_log) for month_log in st.session_state.monthly_logs.values()
        )
        total_cost = sum(st.session_state.monthly_op_costs.values())
        profit = total_revenue - total_cost
        st.table(pd.DataFrame.from_dict({
            'Total Revenue': f"{total_revenue:.2f}",
            'Total Costs': f"{total_cost:.2f}",
            'Profit': f"{profit:.2f}"
        }, orient="index", columns=["₹"]))
    st.markdown("")


def render_monthly_summary(expanded=True):
    this_month = st.session_state.month
    with st.expander("📈 This Month", expanded=expanded):
        if this_month > 0:
            month_log = st.session_state.monthly_logs.get(this_month, [])
            if month_log:
                df_log = pd.DataFrame(month_log)
                summary = df_log.groupby("plant").agg(
                    Died=("status", lambda x: (x == "dead").sum()),
                    Harvested=("status", lambda x: (x == "harvested").sum()),
                    Revenue=("revenue", "sum")
                )
                summary['Cost'] = st.session_state.monthly_op_costs.get(this_month, 0.0)
                st.dataframe(summary)
            else:
                st.info("No changes this month.")
        else:
            st.info("No data available yet. Simulate a month to see results.")
        st.markdown("")


def render_farm_levels():
    st.markdown("---")
    st.subheader("🛠️ Control Panel")
    with st.expander('🌏 Environment Controls'):
        st.markdown("")
        with st.container():
            col1, col2 = st.columns([1, 2], gap="medium")
            with col1:
                st.markdown("🌡️ Temperature (°C)")
            with col2:
                temperature = st.select_slider("temperature", options=INPUT_LEVELS["T"], key=f"T",
                                               label_visibility='collapsed')
        with st.container():
            col1, col2 = st.columns([1, 2], gap="medium")
            with col1:
                st.markdown("💧 Humidity (%)")
            with col2:
                humidity = st.select_slider("water", options=INPUT_LEVELS["H"], key=f"H", label_visibility='collapsed')

    st.markdown('')
    tabs = st.tabs(LEVELS)
    for i, level in enumerate(LEVELS):
        with tabs[i]:
            df_level = st.session_state.farm_df[st.session_state.farm_df.level == level]
            level_inputs[level] = {}
            used_area = df_level[df_level["status"] == "growing"]["space"].sum()
            st.markdown(f"###### **Used / Total Space:** {used_area:.2f} / {LEVEL_AREA} m²")
            with st.expander(f'⚙️ {level} Inputs'):
                st.markdown("")
                with st.container():
                    col1, col2 = st.columns([1, 2], gap="medium")
                    with col1:
                        st.markdown("💡 Lighting (DLI)")
                    with col2:
                        lighting = st.select_slider("lighting", options=INPUT_LEVELS["L"], key=f"L_{level}",
                                                    label_visibility='collapsed')
                with st.container():
                    col1, col2 = st.columns([1, 2], gap="medium")
                    with col1:
                        st.markdown("🌧 Water (mL/plant/day)")
                    with col2:
                        water = st.select_slider("water", options=INPUT_LEVELS["W"], key=f"W_{level}",
                                                 label_visibility='collapsed')
                with st.container():
                    col1, col2 = st.columns([1, 2], gap="medium")
                    with col1:
                        st.markdown("🧪 Nutrients (g/plant/day)")
                    with col2:
                        nutrients = st.select_slider("nutrients", options=INPUT_LEVELS["N"], key=f"N_{level}",
                                                     label_visibility='collapsed')
                level_inputs[level] = {
                    "L": lighting,
                    "W": water,
                    "N": nutrients,
                    "T": (temperature - 0.1) if level == LEVELS[0] else (temperature + 0.1) if level == LEVELS[
                        -1] else temperature,
                    "H": (humidity - 0.1) if level == LEVELS[0] else (humidity + 0.1) if level == LEVELS[
                        -1] else humidity
                }
            with st.expander(f'🌱 Plant Seeds on {level}'):
                with st.form(f"plant_form_{level}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        plant_type = st.selectbox("Plant Type", list(PLANTS.keys()), key=f"pt_{level}")
                    with col2:
                        num_plants = st.number_input("Number of Seeds to Plant", min_value=1, max_value=10000, value=1,
                                                     key=f"np_{level}")
                    submitted = st.form_submit_button("🌱 Plant Seeds")
                    if submitted:
                        plant = PLANTS[plant_type]
                        needed_area = plant["space_required"] * num_plants
                        if needed_area > LEVEL_AREA - used_area:
                            st.error(f"Not enough space on {level}. Available: {LEVEL_AREA - used_area:.2f} m²")
                        elif st.session_state.budget < plant["seed_cost"] * num_plants:
                            st.error("Insufficient budget to plant these seeds.")
                        else:
                            for _ in range(num_plants):
                                new_row = {
                                    "level": level,
                                    "plant": plant_type,
                                    "day_planted": st.session_state.month * 30,
                                    "age": 0,
                                    "space": plant["space_required"],
                                    "status": "growing"
                                }
                                st.session_state.farm_df = pd.concat(
                                    [st.session_state.farm_df, pd.DataFrame([new_row])], ignore_index=True)
                                st.session_state.budget -= plant["seed_cost"]
                            st.success(f"Planted {num_plants} {plant_type} seeds on {level}!")
                            st.rerun()
            df_sorted = df_level.copy()
            df_sorted["status_order"] = df_sorted["status"].map({"growing": 0, "harvested": 1, "dead": 2})
            df_sorted = df_sorted.sort_values("status_order")
            df_sorted["selected"] = False
            edited_df = st.data_editor(
                df_sorted.drop(columns=["status_order"]),
                key=f"editor_{level}",
                num_rows="dynamic",
                use_container_width=True,
                column_order=["selected", "plant", "status", "age", "space", "day_planted", "level"],
                disabled=["plant", "status", "age", "space", "day_planted", "level"]
            )
            selected = edited_df[edited_df["selected"]].index.tolist()
            if selected:
                if st.button("Remove Selected Plants", key=f"delete_rows_{level}"):
                    st.session_state.farm_df.drop(index=selected, inplace=True)
                    st.rerun()


def main():
    st.set_page_config("Saksham | My Vertical Farm", page_icon="🌱", layout="centered", initial_sidebar_state="expanded")
    st.markdown('''
    <div style="display: flex; justify-content: center; align-items: center; gap: 32px; margin-bottom: 0.5em;">
        <span style="font-size: 2em;">🥬🥒🍅</span>
        <span style="font-size: 2em; font-weight: bold;">My Vertical Farm</span>
        <span style="font-size: 2em;">🍐🍓🍇</span>
    </div>
    ''', unsafe_allow_html=True)
    st.markdown('---')
    initialize_session_state()
    render_sidebar()
    expanded = st.session_state.get("_just_simulated", False)
    render_monthly_summary(expanded=expanded)

    # Load custom CSS from static file
    with open(os.path.join(os.path.dirname(__file__), "static", "custom.css")) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    st.markdown('<div class="centered-btn-container">', unsafe_allow_html=True)
    if st.session_state.month < 12:
        simulate_button = st.button("▶▶ Simulate Next Month", key="simulate_next_month")
    else:
        simulate_button = st.button("Complete Simulation 🚩", key="simulate_complete")
    st.markdown('</div>', unsafe_allow_html=True)

    if simulate_button:
        simulate_month()
        st.success("Month simulated!")
        st.session_state["_just_simulated"] = True
        st.rerun()
    st.session_state["_just_simulated"] = False
    render_farm_levels()


if __name__ == "__main__":
    main()
