import random

import numpy as np
import streamlit as st

from vertical_farm.data import PLANTS

STARTING_BUDGET = 10000.0  # Starting budget in Rs.
PRICES = {"Tomato": 30, "Lettuce": 60}
LEVELS = ["Level 1", "Level 2", "Level 3"]
LEVEL_AREA = 25.0  # m^2 per level
INPUT_VARS = ["N", "W", "L", "T", "H"]  # Nutrients, Water, Light, Temperature, Humidity
INPUT_LEVELS = {"N": [x for x in range(0, 51)], "W": [x for x in range(0, 1001, 10)], "L": [x for x in range(0, 31)],
    "T": [x for x in range(10, 46)], "H": [x for x in range(0, 101, 5)]}
RENT = LEVEL_AREA * 100

env_inputs = {"T": 24, "H": 50.0}
level_inputs = {x: {k: v[0] for k, v in INPUT_LEVELS.items()} for x in LEVELS}


def _to_human_readable(var):
    dictionary = {"N": "nutrients", "W": "water", "L": "light", "T": "temperature", "H": "humidity"}
    return dictionary.get(var, var)


def _format_list(items):
    if not items:
        return ""
    elif len(items) == 1:
        return items[0]
    elif len(items) == 2:
        return f"{items[0]} and {items[1]}"
    else:
        return f"{', '.join(items[:-1])}, and {items[-1]}"


def response(x, ideal, tolerance):
    if abs(x - ideal) <= tolerance:
        return random.choice([1.0, 0.99, 0.98, 0.97, 0.96, 0.95])  # Randomly choose between 1.0 and 0.95 for ideal conditions
    elif abs(x - ideal) <= 2 * tolerance:
        return random.choice([0.85, 0.86, 0.87, 0.88, 0.89, 0.9, 0.91, 0.92, 0.93, 0.94])  # Randomly choose between 0.85 and 0.9 for near-ideal conditions
    elif abs(x - ideal) <= 3 * tolerance:
        return random.choice([0.7, 0.75, 0.8])  # Randomly choose between 0.7 and 0.8 for moderate conditions
    else:
        return 0.5


def plant_health_score(plant, env):
    min_r = 1.0
    for var in INPUT_VARS:
        r = response(env[var], plant["ideal"][var], plant["tolerance"][var])
        if r < min_r:
            min_r = r
    return min_r


def get_plant_yield(plant, health_score):
    return round(plant["Gmax"] * health_score, 0)


def simulate_disturbance(plant, env):
    # Find disturbance probability based on plant type and environment
    max_percent_difference = 0
    adverse_variables = []

    for var in INPUT_VARS:
        if (plant['ideal'][var] - plant['tolerance'][var]) <= env[var] <= (
                plant['ideal'][var] + plant['tolerance'][var]):
            continue
        adverse_variables.append(var)
        if env[var] > plant['ideal'][var]:
            percent_difference = abs(env[var] - (plant["ideal"][var] + plant['tolerance'][var])) / plant["tolerance"][var]
        else:
            percent_difference = abs((plant["ideal"][var] - plant['tolerance'][var]) - env[var]) / plant["tolerance"][var]
        if percent_difference > max_percent_difference:
            max_percent_difference = percent_difference
    return np.random.rand() > (1.0 - ((max_percent_difference**2) * 0.1)), adverse_variables


def calculate_month_cost():
    seed_costs = 0
    elec_costs = 0
    water_costs = 0
    nutrients_costs = 0
    rent_costs = RENT
    for level in LEVELS:
        new_plants = st.session_state.month_changes[st.session_state.month]['levels'][level]['new_plants']
        for plant in new_plants:
            plant_info = PLANTS[plant]
            seed_costs += plant_info["seed_cost"] * new_plants[plant]
    for level in LEVELS:
        env = level_inputs[level]
        elec_costs += round(0.0648 * LEVEL_AREA * 2 * env['L'])  # 0.0648 KWh / DLI / m^2 / month * Rs.2 per KWh
        elec_costs += round(1.00 * LEVEL_AREA * abs(env['T'] - 25))  # 1 Rs. / C / m^2 / month
        elec_costs += round(1.00 * LEVEL_AREA * abs(env['H'] - 30))  # 1 Rs. / %RH / m^2 / month
        elec_costs += round(1.00 * LEVEL_AREA * env['W'] / 1000.0)  # 1 Rs. / L / m^2 / month
        water_costs += round(1.50 * LEVEL_AREA * env['W'] / 1000.0)
        nutrients_costs += round(5.00 * LEVEL_AREA * env['N'])  # 0.05 Rs. / N / m^2 / month

    month_cost = round(rent_costs + seed_costs + elec_costs + water_costs + nutrients_costs, 2)

    return month_cost, rent_costs, seed_costs, elec_costs, water_costs, nutrients_costs


def simulate_month():
    updates = []
    monthly_update = []

    # Remove plants that are not growing anymore
    st.session_state.farm_df.drop(index=st.session_state.farm_df[st.session_state.farm_df["status"] != "Growing"].index,
                                    axis=0, inplace=True)

    # Choose random market prices for each plant based on binomial distribution
    for plant in PLANTS:
        st.session_state.market_prices[plant] = np.random.binomial(1, 0.5, 1)[0] * (
                    PLANTS[plant]["price_range"][1] - PLANTS[plant]["price_range"][0]) + PLANTS[plant]["price_range"][0]

    # Calculate the monthly costs
    month_cost, rent_cost, seeds_cost, elec_cost, water_cost, nutrients_cost = calculate_month_cost()

    # Increment the age of all plants by one month
    st.session_state.farm_df.loc[:, "age"] += 30

    # Simulate plant growth and disturbances
    for idx, row in st.session_state.farm_df.iterrows():
        if row["status"] == "Growing":
            plant = PLANTS[row["plant"]]
            env = level_inputs[row["level"]].copy()
            dead, adverse_variables = simulate_disturbance(plant, env)
            if dead:
                reasons = [_to_human_readable(x) for x in adverse_variables]
                updates.append((idx, f"Dead - Unbalanced {_format_list(reasons)}", 0.0, 0))
            elif row["age"] >= plant["growth_days"]:
                yield_kg = get_plant_yield(plant, row["health"])
                st.session_state.harvest_store[row["plant"]] += yield_kg
                updates.append((idx, "Harvested", row["health"], 0))
            else:
                health_score = plant_health_score(plant, env)
                updates.append((idx, "Growing", round(health_score * row["health"], 2), 0))

    st.session_state.budget -= month_cost

    # Update the farm DataFrame and monthly logs
    for idx, status, health, reward in updates:
        st.session_state.farm_df.at[idx, "status"] = status
        st.session_state.budget += reward
        monthly_update.append(
            {"plant": st.session_state.farm_df.at[idx, "plant"], "level": st.session_state.farm_df.at[idx, "level"],
             "status": status, "health": health, "revenue": reward})
    st.session_state.monthly_logs[st.session_state.month] = monthly_update
    st.session_state.monthly_costs[st.session_state.month] = {"rent": rent_cost, "seeds": seeds_cost,
        "electricity": elec_cost, "water": water_cost, "nutrients": nutrients_cost, 'overall': month_cost}

    # Increment the month
    st.session_state.month += 1
    return


def generate_market_day_customers():
    # Generate customers and their demands based on market demand
    customers = []
    for i in range(10):
        customer = {
            "id": i + 1,
            "demand": {},
            "min_price": 0,
            "max_price": 0,
            "accepted": False
        }
        for item, price in st.session_state.market_prices.items():
            if np.random.rand() < 0.5:
                qty = random.randint(1, 5)
                customer["demand"][item] = qty
        if customer["demand"]:
            customer["min_price"] = min(
                price for item, price in st.session_state.market_prices.items() if item in customer["demand"])
            customer["max_price"] = max(
                price for item, price in st.session_state.market_prices.items() if item in customer["demand"])
            customers.append(customer)
    st.session_state.customers = customers