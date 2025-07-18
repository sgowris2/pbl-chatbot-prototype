

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