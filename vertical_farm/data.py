lettuce = {
    "name": "Lettuce",
    "Gmax": 0.25,    # Maximum yield - kg per plant
    "growth_days": 29,
    "space_required": 0.05,  # m^2 per plant
    "ideal": {"N": 2.5, "W": 1250, "L": 15, "T": 21, "H": 60},
    "tolerance": {"N": 1.5, "W": 250, "L": 2, "T": 3, "H": 20},
    "seed_cost": 5, # Rs. per seed
    "supply_chain_cost_per_kg": 50
}
microgreens = {
    "name": "Microgreens",
    "Gmax": 0.001,    # Maximum yield - kg per plant
    "growth_days": 29,
    "space_required": 0.0005, # m^2 per plant
    "ideal": {"N": 1, "W": 400, "L": 14, "T": 23, "H": 50},
    "tolerance": {"N": 1, "W": 100, "L": 2, "T": 4, "H": 20},
    "seed_cost": 0.1,
    "supply_chain_cost_per_kg": 300
}
mushroom = {
    "name": "Mushroom",
    "Gmax": 0.030,    # Maximum yield - kg per plant
    "growth_days": 29,
    "space_required": 0.003, # m^2 per plant
    "ideal": {"N": 3, "W": 1500, "L": 2, "T": 24, "H": 90},
    "tolerance": {"N": 1, "W": 500, "L": 2, "T": 10, "H": 10},
    "seed_cost": 0.1,
    "supply_chain_cost_per_kg": 30
}
strawberry = {
    "name": "Strawberry",
    "Gmax": 0.2,    # Maximum yield - kg per plant
    "growth_days": 89,
    "space_required": 0.05, # m^2 per plant
    "ideal": {"N": 5, "W": 3000, "L": 21, "T": 20, "H": 50},
    "tolerance": {"N": 2, "W": 1000, "L": 4, "T": 4, "H": 20},
    "seed_cost": 0.1,
    "supply_chain_cost_per_kg": 70
}
tomato = {
    "name": "Tomato (cherry)",
    "Gmax": 3,    # Maximum yield - kg per plant
    "growth_days": 59,
    "space_required": 0.25,  # m^2 per plant
    "ideal": {"N": 7, "W": 4500, "L": 25, "T": 23, "H": 70},
    "tolerance": {"N": 2, "W": 1000, "L": 5, "T": 4, "H": 20},
    "seed_cost": 0.1,
    "supply_chain_cost_per_kg": 30
}

PLANTS = {"Lettuce": lettuce,
          "Microgreens": microgreens,
          "Mushroom": mushroom,
          "Strawberry": strawberry,
          "Tomato (cherry)": tomato}

ITEM_ICONS = {"Lettuce": "🥬", "Microgreens": "🌱", "Mushroom": "🍄‍🟫", "Strawberry": "🍓", "Tomato (cherry)": "🍅"}

MARKET_DEMAND_RATIOS = {
    "Lettuce": 0.20,
    "Microgreens": 0.10,
    "Mushroom": 0.25,
    "Strawberry": 0.25,
    "Tomato (cherry)": 0.5
}
