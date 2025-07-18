import numpy as np
import streamlit as st

from vertical_farm.data import PLANTS


LEVELS = ["Level 1", "Level 2", "Level 3"]
LEVEL_AREA = 25.0  # m^2 per level
INPUT_VARS = ["N", "W", "L", "T", "H"]  # Nutrients, Water, Light, Temperature, Humidity
INPUT_LEVELS = {
    "N": [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 44, 46, 48, 50, 52, 54, 56, 58, 60],
    "W": [0, 50, 100, 150, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 750, 800, 850, 900, 950, 1000],
    "L": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30],
    "T": [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40],
    "H": [0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
}

level_inputs = {x: {k: v[0] for k, v in INPUT_LEVELS.items()} for x in LEVELS}


def response(x, ideal, tolerance):
    if abs(x - ideal) <= tolerance:
        return 1.0
    elif abs(x - ideal) <= 2 * tolerance:
        return 0.7
    elif abs(x - ideal) <= 3 * tolerance:
        return 0.4
    else:
        return 0.1

def normalize_inputs(inputs):
    normalized = {}
    for var in INPUT_VARS:
        if var in inputs:
            if isinstance(inputs[var], list):
                normalized[var] = [min(max(v, 0), 1) for v in inputs[var]]
            else:
                normalized[var] = min(max(inputs[var], 0), 1)
        else:
            normalized[var] = 0.0
    return normalized

def plant_growth_score(plant, env):
    min_r = 1.0
    for var in INPUT_VARS:
        r = response(env[var], plant["ideal"][var], plant["tolerance"][var])
        if r < min_r:
            min_r = r
    return plant["Gmax"] * min_r


def simulate_disturbance(plant, env):
    # Find disturbance probability based on plant type and environment
    max_percent_difference = 0
    for var in INPUT_VARS:
        if (plant['ideal'][var] - plant['tolerance'][var]) <= env[var] <= (plant['ideal'][var] + plant['tolerance'][var]):
            continue
        percent_difference = abs(env[var] - plant["ideal"][var]) / plant["ideal"][var]
        if percent_difference > max_percent_difference:
            max_percent_difference = percent_difference
    return np.random.rand() > (1 - max_percent_difference)


def simulate_month():
    monthly_update = []
    monthly_op_cost = 0
    st.session_state.month += 1
    st.session_state.farm_df["age"] += 30
    updates = []
    for idx, row in st.session_state.farm_df.iterrows():
        if row["status"] != "growing":
            continue
        plant = PLANTS[row["plant"]]
        env = normalize_inputs(level_inputs[row["level"]])
        score = plant_growth_score(plant, env)
        if simulate_disturbance(plant, env):
            updates.append((idx, "dead", 0))
        elif row["age"] >= plant["growth_days"]:
            yield_kg = score * plant["yield_per_plant"]
            revenue = round(yield_kg * st.session_state.market_prices[row["plant"]], 2)
            updates.append((idx, "harvested", revenue))
    for level in LEVELS:
        env = normalize_inputs(level_inputs[level])
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
    st.session_state.monthly_op_costs[st.session_state.month] = monthly_op_cost
    return
