import random

import numpy as np
import streamlit as st

from vertical_farm.data import PLANTS, MARKET_DEMAND_RATIOS

STARTING_BUDGET = 10000.0  # Starting budget in Rs.
LEVELS = ["Level 1", "Level 2", "Level 3"]
LEVEL_AREA = 10.0  # m^2 per level
FARM_AREA = LEVEL_AREA * len(LEVELS)  # Total farm area in m^2
INPUT_VARS = ["N", "W", "L", "T", "H"]  # Nutrients, Water, Light, Temperature, Humidity
INPUT_VARS_VALUES_LIST = {
    "N": [x for x in range(0, 51)],
    "W": [x for x in range(0, 1001, 10)],
    "L": [x for x in range(0, 31)],
    "T": [x for x in range(10, 46)],
    "H": [x for x in range(0, 101, 5)]
}
STARTING_ENV_INPUTS = {"T": 24, "H": 50.0}
STARTING_LEVEL_INPUTS = {x: {k: v[0] for k, v in INPUT_VARS_VALUES_LIST.items()} for x in LEVELS}
# ---
AMBIENT_TEMP = 24  # Ambient temperature in degC
AMBIENT_HUMIDITY = 50.0  # Ambient humidity in %
RENT = LEVEL_AREA * 100 # Rs. 100 per month per m^2
PRICE_L_PER_DLI_PER_M2_PER_MONTH = 3 * 1.00  # Rs. 2 per KWh and 3 KWh / DLI / m^2 / month
PRICE_T_PER_DEG_C_PER_M2_PER_MONTH = 1.00  # Rs. 1 per degC / m^2 / month
PRICE_H_PER_PERCENT_RH_PER_M2_PER_MONTH = 1.00  # Rs. 1 per %RH / m^2 / month
PRICE_W_PER_ML_PER_DAY_PER_M2_PER_MONTH = 0.002 # Rs. 0.002 per mL/day / m^2 / month
PRICE_N_PER_G_PER_DAY_PER_M2_PER_MONTH = 5  # Rs. 15 per g/day / m^2 / month
# ---
MARKET_DEMAND_BASELINE = {plant: FARM_AREA * ratio * PLANTS[plant]['Gmax'] / PLANTS[plant]['space_required'] for plant, ratio in MARKET_DEMAND_RATIOS.items()}
MARKET_DEMAND_RANGES = {plant: (MARKET_DEMAND_BASELINE[plant], MARKET_DEMAND_BASELINE[plant] * 4) for plant, ratio in MARKET_DEMAND_RATIOS.items()}


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
    return round(plant["Gmax"] * health_score, 1)


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
        env = STARTING_LEVEL_INPUTS[level]
        elec_costs += round(PRICE_L_PER_DLI_PER_M2_PER_MONTH * LEVEL_AREA * env['L'])  # 0.0648 KWh / DLI / m^2 / month * Rs.2 per KWh
        # elec_costs += round(PRICE_T_PER_DEG_C_PER_M2_PER_MONTH * LEVEL_AREA * abs(env['T'] - AMBIENT_TEMP))  # 1 Rs. / degC / m^2 / month
        # elec_costs += round(PRICE_H_PER_PERCENT_RH_PER_M2_PER_MONTH * LEVEL_AREA * abs(env['H'] - AMBIENT_HUMIDITY))  # 1 Rs. / %RH / m^2 / month
        water_costs += round(PRICE_W_PER_ML_PER_DAY_PER_M2_PER_MONTH * LEVEL_AREA * env['W']) # 1.50 Rs. / L/day / m^2 / month
        nutrients_costs += round(PRICE_N_PER_G_PER_DAY_PER_M2_PER_MONTH * LEVEL_AREA * env['N'])  # 5 Rs. / g/day / m^2 / month

    month_cost = round(rent_costs + seed_costs + elec_costs + water_costs + nutrients_costs, 2)

    return month_cost, rent_costs, seed_costs, elec_costs, water_costs, nutrients_costs


def simulate_month():
    updates = []
    monthly_update = []

    # Remove plants that are not growing anymore
    st.session_state.farm_df.drop(index=st.session_state.farm_df[st.session_state.farm_df["status"] != "Growing"].index,
                                    axis=0, inplace=True)

    # Generate market prices for all plants
    generate_market_prices()
    print(st.session_state.market_prices)

    # Calculate the monthly costs
    month_cost, rent_cost, seeds_cost, elec_cost, water_cost, nutrients_cost = calculate_month_cost()

    # Increment the age of all plants by one month
    st.session_state.farm_df.loc[:, "age"] += 30

    # Simulate plant growth and disturbances
    for idx, row in st.session_state.farm_df.iterrows():
        if row["status"] == "Growing":
            plant = PLANTS[row["plant"]]
            env = STARTING_LEVEL_INPUTS[row["level"]].copy()
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

    for k, v in st.session_state.harvest_store.items():
        st.session_state.harvest_store[k] = round(v, 0)

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


def generate_market_prices():
    # Calculate cost per kg of plant
    for name, plant in PLANTS.items():
        yield_per_m2 = plant['Gmax'] / plant[
            'space_required']  # Ideal yield per m^2 = (Gmax kg/plant) / (space per plant m^2/plant)
        elec_cost_per_m2 = plant['ideal']['L'] * PRICE_L_PER_DLI_PER_M2_PER_MONTH * round(plant['growth_days'] / 30, 0)
        water_cost_per_m2 = plant['ideal']['W'] * PRICE_W_PER_ML_PER_DAY_PER_M2_PER_MONTH * round(
            plant['growth_days'] / 30, 0)
        nutrients_cost_per_m2 = plant['ideal']['N'] * PRICE_N_PER_G_PER_DAY_PER_M2_PER_MONTH * round(
            plant['growth_days'] / 30, 0)
        total_cost_per_m2 = elec_cost_per_m2 + water_cost_per_m2 + nutrients_cost_per_m2
        total_cost_per_kg = round((total_cost_per_m2 / yield_per_m2) + plant['supply_chain_cost_per_kg'], 0)
        st.session_state.market_prices[name] = round(total_cost_per_kg * 1.1, 0)


def generate_market_day_customers():

    def split_number_into_chunks(total, chunks=3):
        cuts = sorted(random.sample(range(1, total), chunks - 1))
        cuts = [0] + cuts + [total]
        return [cuts[i + 1] - cuts[i] for i in range(chunks)]

    market_demand = {}
    demand_of_each_customer = {}
    for item in MARKET_DEMAND_RANGES:
        market_demand[item] = int(np.random.uniform(low=MARKET_DEMAND_RANGES[item][0], high=MARKET_DEMAND_RANGES[item][1]))
        demand_of_each_customer[item] = split_number_into_chunks(market_demand[item], random.choice([2, 3, 4]))

    customers = []
    i = 0
    for item in demand_of_each_customer.keys():
        customer_values = demand_of_each_customer[item]
        for cv in customer_values:
            i += 1
            customer_icon = random.choice(["👩", "👨", "👵", "👴", "👩‍🌾", "👨‍🌾", "👩‍🍳", "👨‍🍳", "👩‍💼",
                                       "👨‍💼", "👩‍🎓", "👨‍🎓", "👩‍🔧", "👨‍🔧", "👩‍💻", "👨‍💻"])
            customer = {
                "id": i + 1,
                "icon": customer_icon,
                "demand": (item, cv),
                "max_price": int(st.session_state.market_prices[item] * np.random.uniform(low=0.90, high=1.15) * cv),
                "accepted": False
            }
            customers.append(customer)

    st.session_state.customers = customers