lettuce = {
    "name": "Lettuce",
    "Gmax": 0.5,    # Maximum yield per plant in kg
    "growth_days": 29,
    "space_required": 0.025,
    "ideal": {"N": 0.5, "W": 200, "L": 12, "T": 21, "H": 60},
    "tolerance": {"N": 0.5, "W": 50, "L": 2, "T": 3, "H": 10},
    "price_range": [150, 250], # Rs. per kg
    "seed_cost": 1 # Rs. per seed
}
tomato = {
    "name": "Tomato",
    "Gmax": 2.5,    # Maximum yield per plant in kg
    "growth_days": 89,
    "space_required": 0.2,
    "ideal": {"N": 30, "W": 750, "L": 25, "T": 23, "H": 70},
    "tolerance": {"N": 5, "W": 250, "L": 5, "T": 4, "H": 10},
    "price_range": [30, 80],
    "seed_cost": 0.5
}


PLANTS = {"Lettuce": lettuce, "Tomato": tomato}
ITEM_ICONS = {"Lettuce": "🥬", "Tomato": "🍅"}

MARKET_DEMAND_RATIOS = {
    "Lettuce": 0.02,
    "Tomato": 0.5
}
