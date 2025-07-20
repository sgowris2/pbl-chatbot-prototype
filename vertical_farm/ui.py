import os
import random
import sys
import uuid

import pandas as pd
import streamlit as st
from anyio import create_udp_socket

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from vertical_farm.data import PLANTS, ITEM_ICONS
from vertical_farm.simulator import simulate_month, STARTING_BUDGET, LEVELS, LEVEL_AREA, INPUT_VARS_VALUES_LIST, STARTING_LEVEL_INPUTS, STARTING_ENV_INPUTS, generate_market_day_customers
from vertical_farm.ui_callbacks import _update_monthly_changes, _disable_simulate, _check_justifications


def initialize_session_state():
    if "user_id" not in st.session_state:
        st.session_state.user_id = str(uuid.uuid4())
        st.session_state.screen = "farm"
        st.session_state.month = 0
        st.session_state.monthly_costs = dict()
        st.session_state.budget = STARTING_BUDGET
        st.session_state.farm_df = pd.DataFrame(columns=[
            "level", "plant", "day_planted", "age", "space", "status", "health"
        ])
        st.session_state.STARTING_ENV_INPUTS = STARTING_ENV_INPUTS
        st.session_state.STARTING_LEVEL_INPUTS = STARTING_LEVEL_INPUTS
        st.session_state.market_prices = dict()
        st.session_state.monthly_logs = {}
        st.session_state.month_start_state = \
            {
                'farm_df': st.session_state.farm_df.__deepcopy__(),
                'levels': STARTING_LEVEL_INPUTS.copy(),
                'env': STARTING_ENV_INPUTS.copy()
            }
        st.session_state.month_changes = {
            x:{
                'environment': {'T': None, 'H': None},
                'levels': {l: {'N': None, 'W': None, 'L': None, 'new_plants': {}} for l in LEVELS}
            } for x in range(13)
        }
        st.session_state._environment_controls_expanded = False
        st.session_state._inputs_expanded = {l: False for l in LEVELS}
        st.session_state._plant_seeds_expanded = {l: False for l in LEVELS}
        st.session_state.harvest_store = {x: 0 for x in PLANTS.keys()}
        st.session_state.customers = [{
            "id": 1,
            "demand": {},
            "min_price": 0,
            "max_price": 0,
            "accepted": False
        }]
        st.session_state.current_customer = 0
        st.session_state.enough = True
        st.session_state.customer_offer_submitted = False
        st.session_state.customer_offer_result = None
        st.session_state.revenue = 0
        st.session_state.results = []

def sidebar():
    st.sidebar.header("Info Panel")
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"👤 **User:** `{st.session_state.user_id[-5:]}`")
    st.sidebar.markdown(f"🗓 **Month:** {st.session_state.month} / 12")
    st.sidebar.markdown(f"💰 **Cash:** ₹{st.session_state.budget:.2f}")
    st.sidebar.markdown("###")
    with st.sidebar:
        performance_panel()

    if st.sidebar.button('ⓘ Factsheet', key="factsheet_button"):
        fact_sheet()


@st.dialog("ⓘ Factsheet", width="large")
def fact_sheet():
    data = [
        ["Lettuce", "Leafy Green", 1, "18–24", "50–70", "150–250", "10–14", "0.15–0.25", 0.025, 0.24, "₹150–250"],
        ["Spinach", "Leafy Green", 1, "16–22", "50–70", "150–250", "12–17", "0.20–0.30", 0.030, 0.15, "₹40–70"],
        ["Kale", "Leafy Green", 2, "16–22", "50–70", "150–250", "12–17", "0.20–0.30", 0.040, 0.20, "₹150–300"],
        ["Swiss Chard", "Leafy Green", 2, "18–24", "50–70", "150–250", "12–17", "0.20–0.30", 0.040, 0.30, "₹100–200"],
        ["Arugula", "Leafy Green", 1, "18–24", "50–70", "150–250", "10–14", "0.15–0.25", 0.020, 0.05, "₹300–400"],
        ["Basil", "Herb", 1, "20–27", "50–70", "150–250", "14–18", "0.15–0.25", 0.030, 0.05, "₹400–600"],
        ["Cilantro", "Herb", 1, "18–22", "50–70", "150–250", "14–18", "0.15–0.25", 0.025, 0.05, "₹80–150"],
        ["Microgreens", "Leafy Green", 0, "20–24", "60–80", "100–150", "10–14", "0.05–0.10", 0.005, 0.03, "₹800–1200"],
        ["Tomato (cherry)", "Fruit Crop", 3, "22–26", "60–80", "700–850", "22–26", "25–35", 0.150, 4.5, "₹80–150"],
        ["Tomato (normal)", "Fruit Crop", 4, "20–26", "60–80", "700–850", "22–26", "25–35", 0.200, 5.0, "₹30–80"],
        ["Cucumber", "Fruit Crop", 2, "24–28", "70–90", "700–850", "22–26", "25–35", 0.120, 2.5, "₹30–60"],
        ["Strawberry", "Fruit Crop", 4, "18–24", "60–80", "300–400", "14–18", "25–35", 0.100, 0.3, "₹200–400"],
        ["Bell Pepper", "Fruit Crop", 3, "19–23", "60–80", "400–500", "18–22", "15–25", 0.100, 1.5, "₹60–120"],
        ["Eggplant", "Fruit Crop", 3, "21–26", "60–80", "400–500", "18–22", "20–30", 0.120, 1.8, "₹30–70"],
        ["Beans (bush)", "Fruit Crop", 3, "20–28", "60–80", "350–450", "18–22", "15–25", 0.080, 0.4, "₹40–80"],
        ["Cauliflower", "Root Crop", 3, "16–20", "60–70", "400–600", "14–16", "12–18", 0.180, 0.8, "₹30–70"],
        ["Carrot", "Root Crop", 3, "16–22", "60–70", "250–400", "14–16", "10–15", 0.060, 0.2, "₹30–60"],
        ["Potato", "Tuber Crop", 4, "15–20", "60–70", "300–400", "14–16", "15–20", 0.080, 1.0, "₹20–40"],
        ["Onion", "Bulb Crop", 5, "15–25", "50–70", "250–350", "14–16", "10–15", 0.060, 0.4, "₹20–40"],
        ["Pumpkin", "Gourd Crop", 5, "20–30", "60–80", "700–900", "18–22", "35–50", 0.500, 3.0, "₹20–40"],
        ["Mushrooms", "Fungi", 1, "18–22", "85–95", "200–300", "5", "3–7", 0.020, 0.2, "₹100–250"]
    ]
    columns = [
        "Crop", "Category", "Months to Maturity", "Temp (°C)", "Humidity (%)",
        "Water (mL/day)", "Light (DLI)", "Nutrients (g/day)",
        "Space (m²/plant)", "Yield (kg/plant)", "Price (₹/kg)"
    ]
    df = pd.DataFrame(data, columns=columns)
    st.table(df)


def market_day_screen():

    no_of_customers = len(st.session_state.customers)
    idx = st.session_state.current_customer
    if idx >= no_of_customers:
        st.session_state.screen = "summary"
        st.rerun()

    customer = st.session_state.customers[idx]
    customer_item = customer["demand"][0]
    customer_qty = customer["demand"][1]

    st.header(f"🧺 Market Day #{st.session_state.month + 1}")
    st.markdown("Welcome to the market day! You will meet several customers today. "
                "Each customer has specific demands and a maximum price they are willing to pay. "
                "Your goal is to sell your produce at fair prices. "
                "Remember that customers only listen to one offer.")
    st.markdown('')
    with st.container(border=1):
        st.write(f"**Your Produce**:")
        for store_item, store_qty in st.session_state.harvest_store.items():
            item_icon = ITEM_ICONS.get(store_item, "📦")  # Default icon if not found
            st.write(f"{store_item} {item_icon}  :  {store_qty}kg")
    st.markdown("---")
    st.markdown(f"### {customer['icon']} Customer {idx + 1} of {no_of_customers}")
    st.write("#### Asking for:\n")
    item_icon = ITEM_ICONS.get(customer_item, "📦")  # Default icon if not found
    st.write(f"{customer_item} {item_icon}  :  {customer_qty}kg")
    st.markdown('')

    col1, col2 = st.columns([2, 1], gap='small', vertical_alignment='bottom')

    with col1:
        offer = st.number_input("Enter your total offer price (₹)", min_value=0, key=f"offer_{idx}",
                                disabled=st.session_state.customer_offer_submitted)

    with col2:
        if st.button("➤ Submit Offer", key=f"submit_{idx}", disabled=st.session_state.customer_offer_submitted):
            customer['accepted'] = False
            st.session_state.enough = st.session_state.harvest_store.get(customer_item, 0) >= customer_qty
            if st.session_state.enough:
                accepted = offer <= customer["max_price"]
                if accepted:
                    st.session_state.customer_offer_result = "accepted"
                    st.session_state.revenue += offer
                    customer['accepted'] = True
                    st.session_state.harvest_store[customer_item] -= customer_qty
                else:
                    st.session_state.customer_offer_result = "rejected"
            else:
                st.session_state.customer_offer_result = "skipped"

            st.session_state.customer_offer_submitted = True
            st.rerun()

    if st.session_state.customer_offer_submitted:
        if not st.session_state.enough:
            st.error("❌ Not enough inventory.")
        else:
            if customer['accepted']:
                st.success("✅ Offer Accepted!")
            else:
                st.warning("❌ Offer Rejected.")
    else:
        st.info("Submit an offer or skip this customer.")

    st.markdown('')
    if st.button(f"{'⏩ Next' if st.session_state.customer_offer_submitted else '❌ Skip'} Customer", key=f"skip_customer"):
        st.session_state.results.append({
            "customer": idx,
            "item": customer_item,
            "qty": customer_qty,
            "offer_result": st.session_state.customer_offer_result if st.session_state.customer_offer_result else "skipped",
            "offer_price": offer if offer else None,
            "customer_max_price": customer["max_price"]
        })
        st.session_state.current_customer += 1
        st.session_state.customer_offer_submitted = False
        st.session_state.customer_offer_result = None
        st.rerun()


def summary_screen():
    st.header(f"📊 Market Day #{st.session_state.month + 1} Summary")
    st.markdown("Welcome to the market day! You will meet 10 customers today. "
                "Each customer has specific demands and a maximum price they are willing to pay. "
                "Your goal is to sell your produce at fair prices. "
                "Remember that customers only listen to one offer.")
    st.markdown('')
    with st.container(border=1):
        st.markdown(f"##### 💰 You sold produce worth: ₹{st.session_state.revenue}")

    st.markdown('')
    st.write("**Results:**")
    for res in st.session_state.results:
        if res["offer_result"] == "accepted":
            status = "✅ Accepted"
            st.success(f"Customer {res['customer'] + 1} wanted {res['qty']}kg {res['item']} @ ₹{res['customer_max_price']}  --  {status} at ₹{res['offer_price']}")
        elif res["offer_result"] == "rejected":
            status = "❌ Rejected"
            st.error(f"Customer {res['customer'] + 1} wanted {res['qty']}kg {res['item']} @ ₹{res['customer_max_price']}  --  {status} at ₹{res['offer_price']}")
        else:
            status = "🙅🏻‍♂️ Skipped"
            st.warning(f"Customer {res['customer'] + 1} wanted {res['qty']}kg {res['item']} @ ₹{res['customer_max_price']}  --  {status}")

    st.write("**Wasted Produce:**")
    for item, qty in st.session_state.harvest_store.items():
        item_icon = ITEM_ICONS.get(item, "📦")  # Default icon if not found
        st.write(f"{item} {item_icon}  :  {qty}kg")

    if st.button("🚜 Back To The Farm", key=f"back_to_farm"):
        st.session_state.current_customer = 0
        st.session_state.screen = "farm"
        st.rerun()


def performance_panel(expanded=True):
    with st.expander("📊 Farm Performance", expanded=expanded):
        total_revenue = st.session_state.revenue
        total_cost = sum([x['overall'] for x in st.session_state.monthly_costs.values()])
        profit = total_revenue - total_cost
        st.table(pd.DataFrame.from_dict({
            'Total Revenue': f"{total_revenue:.2f}",
            'Total Costs': f"{total_cost:.2f}",
            'Profit': f"{profit:.2f}"
        }, orient="index", columns=["₹"]))
    st.markdown("")


def this_month_results(expanded=True):
    this_month = st.session_state.month - 1
    with st.expander("📈 This Month's Results", expanded=expanded):
        if this_month >= 0:
            month_log = st.session_state.monthly_logs.get(this_month, [])
            if month_log:
                df_log = pd.DataFrame(month_log)
                summary = df_log.groupby("plant").agg(
                    died=("status", lambda x: (x.str.contains("Dead")).sum()),
                    harvested=("status", lambda x: (x == "Harvested").sum()),
                    revenue=("revenue", "sum")
                )
                st.dataframe(summary)
                st.markdown("**Total Monthly Cost**: ₹{:.2f}".format(st.session_state.monthly_costs.get(this_month, 0.0)['overall']))
                st.markdown("Rent: ₹{:.2f}".format(st.session_state.monthly_costs.get(this_month, 0.0)['rent']))  # Assuming half for rent
                st.markdown("Seeds Cost: ₹{:.2f}".format(st.session_state.monthly_costs.get(this_month, 0.0)['seeds']))
                st.markdown("Electricity Cost: ₹{:.2f}".format(st.session_state.monthly_costs.get(this_month, 0.0)['electricity']))
                st.markdown("Water Cost: ₹{:.2f}".format(st.session_state.monthly_costs.get(this_month, 0.0)['water']))
                st.markdown("Nutrients Cost: ₹{:.2f}".format(st.session_state.monthly_costs.get(this_month, 0.0)['nutrients']))
            else:
                st.info("No changes this month.")
        else:
            st.info("No data available yet. Simulate a month to see results.")
        st.markdown("")


def control_panel():
    st.markdown("---")
    st.subheader("🛠️ Control Panel")
    temperature, humidity = env_controls()
    st.markdown('')
    tabs = st.tabs(LEVELS)
    for i, level in enumerate(LEVELS):
        with tabs[i]:
            df_level = st.session_state.farm_df[st.session_state.farm_df.level == level]
            used_area = df_level[df_level["status"] == "Growing"]["space"].sum()
            st.markdown(f"###### **Used / Total Space:** {used_area:.2f} / {LEVEL_AREA} m²")
            lighting, water, nutrients = level_inputs_controls(level)
            plant_seeds_form(level, used_area)
            STARTING_ENV_INPUTS["T"] = temperature
            STARTING_ENV_INPUTS["H"] = humidity
            STARTING_LEVEL_INPUTS[level] = {
                "L": lighting,
                "W": water,
                "N": nutrients,
                "T": (temperature - 0.1) if level == LEVELS[0] else (temperature + 0.1) if level == LEVELS[
                    -1] else temperature,
                "H": (humidity - 0.1) if level == LEVELS[0] else (humidity + 0.1) if level == LEVELS[
                    -1] else humidity
            }
            df_sorted = df_level.copy()
            df_sorted["status_order"] = df_sorted["status"].map({"Growing": 0, "Harvested": 1, "Dead": 2})
            df_sorted = df_sorted.sort_values("status_order")
            df_sorted["select"] = False
            df_sorted = df_sorted.reset_index(drop=True)
            df_sorted["health"] = df_sorted["health"].apply(lambda x: f"{x * 100:.0f}%")
            edited_df = st.data_editor(
                df_sorted.drop(columns=["status_order"]),
                key=f"editor_{level}",
                num_rows="dynamic",
                use_container_width=True,
                column_order=["select", "plant", "status", "health", "age"],
                disabled=["plant", "status", "health", "age"],
                hide_index=True
            )
            selected = edited_df[edited_df["select"]].index.tolist()
            if selected:
                if st.button("Remove Selected Plants", key=f"delete_rows_{level}"):
                    st.session_state.farm_df.drop(index=selected, inplace=True)
                    removed_types = edited_df.loc[selected, "plant"].unique()
                    for plant_type in removed_types:
                        num_plants = edited_df.loc[selected, "plant"].value_counts().get(plant_type, 0)
                        if num_plants > 0:
                            _update_monthly_changes(level=level, type='removed_plants', plant=plant_type, num_plants=num_plants)
                    st.rerun()


def env_controls():
    with st.expander('🌏 Environment Controls', expanded=st.session_state._environment_controls_expanded):
        st.markdown("")
        with st.container():
            col1, col2 = st.columns([1, 2], gap="medium")
            with col1:
                st.markdown("🌡️ Temperature (°C)")
            with col2:
                temperature = st.select_slider(
                    "temperature",
                    options=INPUT_VARS_VALUES_LIST["T"],
                    key=f"T",
                    value=st.session_state.T if 'T' in st.session_state else st.session_state.STARTING_ENV_INPUTS["T"],
                    label_visibility='collapsed',
                    on_change=_update_monthly_changes,
                    kwargs={'type': 'environment', 'var': 'T', 'key': 'T'}
                )
        with st.container():
            col1, col2 = st.columns([1, 2], gap="medium")
            with col1:
                st.markdown("💧 Humidity (%)")
            with col2:
                humidity = st.select_slider(
                    "water",
                    options=INPUT_VARS_VALUES_LIST["H"],
                    key=f"H",
                    value=st.session_state.H if 'H' in st.session_state else st.session_state.STARTING_ENV_INPUTS["H"],
                    label_visibility='collapsed',
                    on_change=_update_monthly_changes,
                    kwargs={'type': 'environment', 'var': 'H', 'key': 'H'}
                )
    return temperature, humidity


def level_inputs_controls(level):
    with st.expander(f'⚙️ {level} Inputs', expanded=st.session_state._inputs_expanded[level]):
        st.markdown("")
        with st.container():
            col1, col2 = st.columns([1, 2], gap="medium")
            with col1:
                st.markdown("💡 Lighting (DLI)")
            with col2:
                lighting = st.select_slider(
                    "lighting",
                    options=INPUT_VARS_VALUES_LIST["L"],
                    key=f"L_{level}",
                    value=st.session_state.get(f"L_{level}", st.session_state.STARTING_LEVEL_INPUTS[level]["L"]),
                    label_visibility='collapsed',
                    on_change=_update_monthly_changes,
                    kwargs={'type': 'inputs', 'level': level, 'var': 'L', 'key': f'L_{level}'}
                )
        with st.container():
            col1, col2 = st.columns([1, 2], gap="medium")
            with col1:
                st.markdown("🌧 Water (mL/plant/day)")
            with col2:
                water = st.select_slider(
                    "water",
                    options=INPUT_VARS_VALUES_LIST["W"],
                    key=f"W_{level}",
                    value=st.session_state.get(f"W_{level}", st.session_state.STARTING_LEVEL_INPUTS[level]["W"]),
                    label_visibility='collapsed',
                    on_change=_update_monthly_changes,
                    kwargs={'type': 'inputs', 'level': level, 'var': 'W', 'key': f'W_{level}'}
                )
        with st.container():
            col1, col2 = st.columns([1, 2], gap="medium")
            with col1:
                st.markdown("🧪 Nutrients (g/plant/day)")
            with col2:
                nutrients = st.select_slider(
                    "nutrients",
                    options=INPUT_VARS_VALUES_LIST["N"],
                    key=f"N_{level}",
                    value=st.session_state.get(f"N_{level}", st.session_state.STARTING_LEVEL_INPUTS[level]["N"]),
                    label_visibility='collapsed',
                    on_change=_update_monthly_changes,
                    kwargs={'type': 'inputs', 'level': level, 'var': 'N', 'key': f'N_{level}'}
                )
    return lighting, water, nutrients


def plant_seeds_form(level, used_area):
    with st.expander(f'🌱 Plant Seeds on {level}', expanded=st.session_state._plant_seeds_expanded[level]):
        with st.form(f"plant_form_{level}"):
            col1, col2 = st.columns(2)
            with col1:
                plant_type = st.selectbox("Plant Type", list(PLANTS.keys()), key=f"pt_{level}")
            with col2:
                num_plants = st.number_input("Number of Seeds to Plant", min_value=0, max_value=10000, value=0, key=f"np_{level}")
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
                            "status": "Growing",
                            "health": 1.0  # Initial health is 100%
                        }
                        st.session_state.farm_df = pd.concat([st.session_state.farm_df, pd.DataFrame([new_row])], ignore_index=True)
                    _update_monthly_changes(level=level, type='new_plants', plant=plant_type, num_plants=num_plants)
                    st.success(f"Planted {num_plants} {plant_type} seeds on {level}!")
                    st.rerun()


def change_list():

    def detect_changes():
        changes = []
        if st.session_state.month_changes[st.session_state.month]['environment']['T'] is not None:
            changes.append(
                f"🌡️ Temperature changed from {st.session_state.month_start_state['env']['T']}°C to {st.session_state.month_changes[st.session_state.month]['environment']['T']}°C")
        if st.session_state.month_changes[st.session_state.month]['environment']['H'] is not None:
            changes.append(
                f"💧 Humidity changed from {st.session_state.month_start_state['env']['H']}% to {st.session_state.month_changes[st.session_state.month]['environment']['H']}%")
        for l in LEVELS:
            if st.session_state.month_changes[st.session_state.month]['levels'][l]['N'] is not None:
                changes.append(
                    f"🧪 {l} Nutrients changed from {st.session_state.month_start_state['levels'][l]['N']}g to {st.session_state.month_changes[st.session_state.month]['levels'][l]['N']}g")
            if st.session_state.month_changes[st.session_state.month]['levels'][l]['W'] is not None:
                changes.append(
                    f"🌧 {l} Water changed from {st.session_state.month_start_state['levels'][l]['W']}mL to {st.session_state.month_changes[st.session_state.month]['levels'][l]['W']}mL")
            if st.session_state.month_changes[st.session_state.month]['levels'][l]['L'] is not None:
                changes.append(
                    f"💡 {l} Lighting changed from {st.session_state.month_start_state['levels'][l]['L']}DLI to {st.session_state.month_changes[st.session_state.month]['levels'][l]['L']}DLI")
            for plant, num_plants in st.session_state.month_changes[st.session_state.month]['levels'][l][
                'new_plants'].items():
                if num_plants > 0:
                    changes.append(f"🌱 Added {num_plants} new {plant} plants on {l}")

        if not changes:
            changes.append("No changes yet this month.")

        return changes

    changes = detect_changes()
    with st.container():
        for change in changes:
            st.info(change)


def main():
    # Load custom CSS from static file
    with open(os.path.join(os.path.dirname(__file__), "static", "custom.css")) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
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
    sidebar()
    _just_simulated = st.session_state.get("_just_simulated", False)

    if st.session_state.screen == "market":
        market_day_screen()
    elif st.session_state.screen == "summary":
        summary_screen()
    else:

        with st.container(border=1):
            st.markdown("#### Current Month's Actions")
            change_list()
            st.markdown('')
            notes = st.text_area("📜 Reasons", max_chars=1000, key="monthly_notes", on_change=_disable_simulate)
            st.button("✅ Check Reasoning", key="check_notes", on_click=_check_justifications, kwargs={"notes": notes})
            simulate_disabled = st.session_state.get("simulate_disabled", True)

        st.markdown('<div class="centered-btn-container">', unsafe_allow_html=True)
        st.markdown('')
        if st.session_state.month < 12:
            simulate_button = st.button("▶▶ Simulate Next Month", key="simulate_next_month", disabled=simulate_disabled)
        else:
            simulate_button = st.button("End Game 🚩", key="simulate_complete", disabled=simulate_disabled)
        if simulate_disabled:
            st.warning('Please provide reasons for your actions and get them checked before simulating the next month.', icon="⚠️")
        st.markdown('</div>', unsafe_allow_html=True)

        if simulate_button:
            simulate_month()
            st.success("Month simulated!")
            st.session_state["_just_simulated"] = True
            st.session_state.month_start_state = {
                'farm_df': st.session_state.farm_df.__deepcopy__(),
                'env': st.session_state.STARTING_ENV_INPUTS.copy(),
                'levels': st.session_state.STARTING_LEVEL_INPUTS.copy(),
            }
            st.session_state.screen = "market"
            generate_market_day_customers()
            st.rerun()
        st.session_state["_just_simulated"] = False
        st.markdown('')
        this_month_results(expanded=_just_simulated)
        control_panel()


if __name__ == "__main__":
    main()
