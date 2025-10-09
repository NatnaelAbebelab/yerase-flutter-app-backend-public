from typing import Dict, List

from admins.models import Meal

# ---- calculators ----
def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    if height_cm <= 0:
        raise ValueError("height must be > 0")
    h_m = height_cm / 100.0
    bmi = weight_kg / (h_m * h_m)
    return round(bmi, 2)

def get_body_state(bmi: float) -> str:
    if bmi < 18.5:
        return "Underweight"
    elif bmi < 25:
        return "Normal"
    else:
        return "Overweight"

def calculate_bmr(weight_kg: float, height_cm: float, age: int, gender: str) -> float:
    # Mifflin-St Jeor
    gender = gender.lower()
    if gender not in ("male", "female"):
        raise ValueError("gender must be 'male' or 'female'")
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return round(base + (5 if gender == "male" else -161))

def calculate_macros(calories: int) -> Dict[str, float]:
    # Example ratio: P30 / C40 / F30
    protein_cal = calories * 0.30
    carbs_cal = calories * 0.40
    fats_cal = calories * 0.30
    # grams: protein/carbs = 4 kcal/g, fats = 9 kcal/g
    return {
        "protein_g": round(protein_cal / 4, 1),
        "carbs_g": round(carbs_cal / 4, 1),
        "fats_g": round(fats_cal / 9, 1),
    }

def get_calorie_goals(bmr: int, body_state: str) -> Dict[str, int]:
    """
    Return a dict of goals (key->calories).
    We'll map keys to the names you requested later.
    """
    bmr = int(round(bmr))
    if body_state == "Normal":
        return {"maintainweight": bmr}
    if body_state == "Overweight":
        # mild/slight loss ~ -10%, loss ~ -21%, extreme ~ -40%
        return {
            "maintainweight": bmr,
            "slight": int(round(bmr * 0.9)),
            "extreme": int(round(bmr * 0.6)),
        }
    if body_state == "Underweight":
        # mild/gain ~ +10%, gain ~ +21%, extreme ~ +40%
        return {
            "maintainweight": bmr,
            "slight": int(round(bmr * 1.1)),
            "extreme": int(round(bmr * 1.4)),
        }
    return {"maintainweight": bmr}

# ---- meal selection (max 10) ----
def select_meals_for_goal(target_calories: int, max_meals: int = 10) -> List[dict]:
    """
    Greedy approximation to choose up to max_meals whose combined calories are close to target.
    Strategy:
      - sort meals by calories descending
      - add meal if it doesn't push us beyond 110% of target
      - after first pass, try to fill remaining gap with smallest available meals (to avoid overshoot)
      - fallback: random selection (up to max_meals)
    Returns list of meal dicts.
    """
    meals_qs = Meal.objects.filter(is_deleted=False)
    all_meals = list(meals_qs)
    if not all_meals:
        return []

    # sort desc
    descending = sorted(all_meals, key=lambda m: m.calories, reverse=True)
    selected = []
    total = 0
    upper = target_calories * 1.1
    lower_stop = target_calories * 0.9

    # greedy add the largest meals while staying <= upper and under max_meals
    for m in descending:
        if len(selected) >= max_meals:
            break
        if total + m.calories <= upper:
            selected.append(m)
            total += m.calories
        if total >= lower_stop:
            break

    # If still under lower_stop and we haven't reached max_meals, try adding small meals to fill gap
    if total < lower_stop and len(selected) < max_meals:
        ascending = sorted(all_meals, key=lambda m: m.calories)
        for m in ascending:
            if m in selected:
                continue
            if len(selected) >= max_meals:
                break
            selected.append(m)
            total += m.calories
            if total >= lower_stop:
                break

    # Final fallback: if nothing selected (highly unusual) or still tiny, random pick up to max_meals
    if not selected:
        sample = list(meals_qs.order_by('?')[:max_meals])
        selected = sample
        total = sum(m.calories for m in selected)

    # build return structure (cap at max_meals)
    selected = selected[:max_meals]
    result = []
    for m in selected:
        result.append({
            "name": m.name,
            "category": m.category.name if m.category else None,
            "calorie": int(m.calories),
            "protein": float(m.protein or 0),
            "carbs": float(m.carbs or 0),
            "fats": float(m.fats or 0),
            "image": m.image or ""
        })
    return result
