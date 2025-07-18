tomato = {
    "name": "Tomato",
    "Gmax": 1.0,
    "growth_days": 90,
    "space_required": 0.2,
    "ideal": {"N": 30, "W": 750, "L": 25, "T": 23, "H": 90},
    "tolerance": {"N": 5, "W": 250, "L": 5, "T": 4, "H": 20},
    "price": 12,
    "yield_per_plant": 2.5,  # kg per plant
    "seed_cost": 0.5
}
lettuce = {
    "name": "Lettuce",
    "Gmax": 0.8,
    "growth_days": 60,
    "space_required": 0.1,
    "ideal": {"N": 1.5, "W": 25, "L": 12, "T": 20, "H": 60},
    "tolerance": {"N": 1, "W": 10, "L": 5, "T": 4, "H": 25},
    "price": 8,
    "yield_per_plant": 1,  # kg per plant
    "seed_cost": 0.6
}

PLANTS = {"Tomato": tomato, "Lettuce": lettuce}