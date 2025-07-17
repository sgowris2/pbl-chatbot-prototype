# vertical_farm_ui.py

import streamlit as st
import pandas as pd
import numpy as np
import uuid

# -----------------------------
# Simulation Configurations
# -----------------------------
LEVELS = ["Level 1", "Level 2", "Level 3"]
LEVEL_AREA = 25.0  # m^2 per level
LEVEL_CONDITIONS = {
    "Level 1": {"temp": 0.65, "humidity": 0.55},
    "Level 2": {"temp": 0.75, "humidity": 0.65},
    "Level 3": {"temp": 0.85, "humidity": 0.75},
}
INPUT_VARS = ["N", "W", "L", "T", "H"]  # Nutrients, Water, Light, Temperature, Humidity
INPUT_LEVELS = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]

# Per-level input controls
level_inputs = {x: {v: 0.0 for v in INPUT_VARS} for x in LEVELS}

# Mock plant species dictionary
tomato = {
    "name": "Tomato",
    "Gmax": 1.0,
    "growth_days": 90,
    "space_required": 0.2,
    "ideal": {"N": 0.8, "W": 0.7, "L": 0.9, "T": 0.75, "H": 0.6},
    "tolerance": {"N": 0.2, "W": 0.2, "L": 0.1, "T": 0.1, "H": 0.1},
    "price": 12,
    "yield_per_plant": 2.0,  # kg per plant
    "seed_cost": 5
}
lettuce = {
    "name": "Lettuce",
    "Gmax": 0.8,
    "growth_days": 60,
    "space_required": 0.1,
    "ideal": {"N": 0.6, "W": 0.8, "L": 0.6, "T": 0.7, "H": 0.7},
    "tolerance": {"N": 0.1, "W": 0.1, "L": 0.1, "T": 0.1, "H": 0.1},
    "price": 8,
    "yield_per_plant": 1.5,  # kg per plant
    "seed_cost": 3
}
PLANTS = {"Tomato": tomato, "Lettuce": lettuce}

# -----------------------------
# Utility Functions
# -----------------------------

def response(x, ideal, tolerance):
    if abs(x - ideal) <= tolerance:
        return 1.0
    elif abs(x - ideal) <= 2 * tolerance:
        return 0.7
    elif abs(x - ideal) <= 3 * tolerance:
        return 0.4
    else:
        return 0.1

def plant_growth_score(plant, env):
    min_r = 1.0
    for var in INPUT_VARS:
        r = response(env[var], plant["ideal"][var], plant["tolerance"][var])
        if r < min_r:
            min_r = r
    return plant["Gmax"] * min_r

def simulate_disturbance():
    return np.random.rand() > 0.85  # 15% plant death

# -----------------------------
# Streamlit App
# -----------------------------
st.set_page_config("Vertical Farm Simulator", layout="centered", initial_sidebar_state="expanded")
st.title("🌱 Vertical Farm Simulator")

if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())
    st.session_state.month = 0
    st.session_state.budget = 1000.0
    st.session_state.farm_df = pd.DataFrame(columns=[
        "level", "plant", "day_planted", "age", "space", "status"
    ])
    st.session_state.market_prices = {"Tomato": 12, "Lettuce": 8}
    st.session_state.monthly_logs = {}

st.sidebar.header("Info Panel")
st.sidebar.markdown("###")
st.sidebar.markdown(f"👤 **User:** `{st.session_state.user_id[-5:]}`")
st.sidebar.markdown(f"**Month:** {st.session_state.month} / 12")
st.sidebar.markdown(f"**Budget:** ₹{st.session_state.budget:.2f}")

# Market Overview
st.sidebar.markdown("###")
st.sidebar.subheader("📈 Market Prices")
st.sidebar.table(pd.DataFrame.from_dict(st.session_state.market_prices, orient="index", columns=["₹/kg"]))

# Hidden reset button
if st.sidebar.button("🔄"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
        st.rerun()

# Monthly Simulation Step
monthly_update = []
monthly_op_cost = 0

if st.session_state.month < 12:
    simulate_button = st.button("⏭️ Simulate Next Month")
else:
    simulate_button = st.button("✅ Complete Simulation")

if simulate_button:
    st.session_state.month += 1
    st.session_state.farm_df["age"] += 30

    updates = []
    for idx, row in st.session_state.farm_df.iterrows():
        if row["status"] != "growing":
            continue
        plant = PLANTS[row["plant"]]
        env = level_inputs[row["level"]].copy()
        score = plant_growth_score(plant, env)

        if simulate_disturbance():
            updates.append((idx, "dead", 0))
        elif row["age"] >= plant["growth_days"]:
            yield_kg = score * plant["yield_per_plant"]
            revenue = round(yield_kg * st.session_state.market_prices[row["plant"]], 2)
            updates.append((idx, "harvested", revenue))

    for level in LEVELS:
        env = level_inputs[level]
        print('Env:', env)
        monthly_op_cost += 100 + (20 * env["L"] + 15 * env["W"] + 10 * env["N"])
    st.session_state.budget -= monthly_op_cost

    for idx, status, reward in updates:
        st.session_state.farm_df.at[idx, "status"] = status
        st.session_state.budget += reward
        monthly_update.append({"plant": st.session_state.farm_df.at[idx, "plant"],
                               "level": st.session_state.farm_df.at[idx, "level"],
                               "status": status,
                               "revenue": reward})

    for plant in st.session_state.market_prices:
        change = np.random.uniform(-0.1, 0.1)
        st.session_state.market_prices[plant] *= (1 + change)
        st.session_state.market_prices[plant] = round(st.session_state.market_prices[plant], 2)

    st.session_state.monthly_logs[st.session_state.month] = monthly_update
    st.success("Month simulated!")

# Overall Summary (This Month Only)
st.markdown("##### 📊 This Month")
this_month = st.session_state.month
month_log = st.session_state.monthly_logs.get(this_month, [])

if month_log:
    df_log = pd.DataFrame(month_log)
    print(df_log)
    summary = df_log.groupby("plant").agg(
        Died=("status", lambda x: (x == "dead").sum()),
        Harvested=("status", lambda x: (x == "harvested").sum()),
        Revenue=("revenue", "sum")
    )
    summary['Cost'] = monthly_op_cost
    st.dataframe(summary)
else:
    st.info("No changes this month.")

# Farm Levels
st.markdown("---")
st.header("Your Farm")
tabs = st.tabs(LEVELS)
for i, level in enumerate(LEVELS):
    with tabs[i]:
        df_level = st.session_state.farm_df[st.session_state.farm_df.level == level]
        level_inputs[level] = {}

        used_area = df_level["space"].sum()
        st.markdown(f"##### **Used / Total Space:** {used_area:.2f} / {LEVEL_AREA} m²")

        with st.expander('⚙️ Environment Controls'):
            st.markdown("")
            with st.container():
                col1, col2 = st.columns([1, 4], gap="small")
                with col1:
                    st.markdown("💡 Lighting")
                with col2:
                    lighting = st.select_slider("lighting", options=INPUT_LEVELS, key=f"L_{level}", label_visibility='collapsed')
            with st.container():
                col1, col2 = st.columns([1, 4], gap="small")
                with col1:
                    st.markdown("💧 Water")
                with col2:
                    water = st.select_slider("water", options=INPUT_LEVELS, key=f"W_{level}", label_visibility='collapsed')
            with st.container():
                col1, col2 = st.columns([1, 4], gap="small")
                with col1:
                    st.markdown("🧪 Nutrients")
                with col2:
                    nutrients = st.select_slider("nutrients", options=INPUT_LEVELS, key=f"N_{level}", label_visibility='collapsed')
            level_inputs[level] = {
                "L": lighting,
                "W": water,
                "N": nutrients,
                "T": LEVEL_CONDITIONS[level]["temp"],
                "H": LEVEL_CONDITIONS[level]["humidity"]
            }

        with st.expander('🌱 Plant Seeds'):
            with st.form(f"plant_form_{level}"):
                col1, col2 = st.columns(2)
                with col1:
                    plant_type = st.selectbox("Plant Type", list(PLANTS.keys()), key=f"pt_{level}")
                with col2:
                    num_plants = st.number_input("Number of Seeds to Plant", min_value=1, max_value=100, value=5, key=f"np_{level}")

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
                            st.session_state.farm_df = pd.concat([st.session_state.farm_df, pd.DataFrame([new_row])], ignore_index=True)
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
