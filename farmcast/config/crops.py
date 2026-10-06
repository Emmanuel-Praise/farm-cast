"""Crop advice lookup. Rows are data — add crops without touching rules.py."""
# Keys: category -> crop -> advice (English; Pidgin/Lamnso files mirror structure)

ADVICE = {
    "HEAVY_RAIN": {
        "maize": "Do not plant. Do not apply fertilizer — the rain will wash it away.",
        "beans": "Do not plant. Avoid fertilizer — heavy rain will wash it away and rot seeds.",
        "groundnut": "Do not plant — seeds may rot. Wait for rain to reduce.",
        "cassava": "Delay planting cuttings — waterlogged soil causes rot.",
        "cocoyam": "Do not plant new corms — too much water causes rot.",
        "irish potato": "Do not plant. High blight risk — avoid field work.",
        "vegetables": "Protect nursery beds. Do not transplant seedlings.",
        "coffee": "Do not apply fertilizer. Clear drains around young trees.",
        "plantain": "Do not plant suckers now. Stake existing plants against wind.",
        "default": "Do not plant. Do not apply fertilizer — rain will wash it away.",
    },
    "RAIN": {
        "maize": "Good time to plant. Apply fertilizer after the rain stops.",
        "beans": "Good time to plant beans. Light fertilizer after rain is fine.",
        "groundnut": "Good planting window. Plant on well-drained ridges.",
        "cassava": "Good time to plant cuttings while soil is moist.",
        "cocoyam": "Good time to plant — soil moisture is ideal.",
        "irish potato": "Good for planting. Watch for blight next week.",
        "vegetables": "Good time to transplant. Mulch after rain.",
        "coffee": "Good for planting seedlings. Apply manure in a ring, not broadcast.",
        "plantain": "Good time to plant suckers. Dig wide holes with compost.",
        "default": "Good time to plant. Apply fertilizer after the rain stops.",
    },
    "LIGHT_RAIN": {
        "maize": "Good for planting. Light fertilizer application is okay.",
        "beans": "Plant now — light rain helps germination.",
        "groundnut": "Plant now. Light rain is enough for emergence.",
        "cassava": "Plant cuttings now.",
        "cocoyam": "Good light moisture for planting.",
        "irish potato": "Okay to plant. Keep an eye on watering.",
        "vegetables": "Transplant and water lightly to supplement.",
        "coffee": "Okay for weeding and light manure.",
        "plantain": "Okay to plant with compost and watering.",
        "default": "Good for planting. Light fertilizer is okay.",
    },
    "DRY": {
        "maize": "Water your nursery. Delay planting until rain comes.",
        "beans": "Hold off planting. Water nursery beds.",
        "groundnut": "Do not plant dry soil. Wait for at least 5mm rain.",
        "cassava": "You can prepare ridges, but delay planting cuttings.",
        "cocoyam": "Mulch heavily. Delay new planting.",
        "irish potato": "Irrigate if you can, else wait.",
        "vegetables": "Water nursery every morning. Do not transplant.",
        "coffee": "Mulch young trees. Delay fertilizer.",
        "plantain": "Mulch and water suckers. Delay new planting.",
        "default": "Water your nursery. Delay planting.",
    },
    "DRY_SPELL": {
        "maize": "Do not plant. Water nursery every morning.",
        "beans": "Do not plant. Conserve soil moisture with mulch.",
        "groundnut": "Do not plant during dry spell.",
        "cassava": "Delay planting. Protect cuttings in shade.",
        "cocoyam": "No planting. Keep soil covered.",
        "irish potato": "No planting. Irrigate only early morning if possible.",
        "vegetables": "Water nursery twice daily. No transplanting.",
        "coffee": "Mulch and shade young trees. No fertilizer.",
        "plantain": "No new planting. Mulch heavily.",
        "default": "Do not plant. Water nursery every morning.",
    },
}

SUPPORTED_CROPS = ["maize", "beans", "groundnut", "cassava", "cocoyam",
                   "irish potato", "vegetables", "coffee", "plantain"]


def advice_for(category: str, crop: str) -> str:
    crop = (crop or "").strip().lower()
    table = ADVICE.get(category, ADVICE["DRY"])
    return table.get(crop, table["default"])
