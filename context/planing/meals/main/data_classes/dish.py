
def _get_attribute(attribute):
    return attribute if attribute is not None else "Need to be manually inserted for this dish"


class Dish:
    def __init__(
        self,
        title,
        image_url,
        category,
        time,
        budget_friendly,
        region,
        spicy,
        difficulty,
        description,
        nutritional_info,
        ingredients,
        recipe
    ):
        self.title = _get_attribute(title)
        self.category = _get_attribute(category)
        self.image_url = _get_attribute(image_url)
        self.time = _get_attribute(time)
        self.budget_friendly = _get_attribute(budget_friendly)
        self.region = _get_attribute(region)
        self.spicy = _get_attribute(spicy)
        self.difficulty = _get_attribute(difficulty)
        self.description = _get_attribute(description)
        self.nutritional_info = _get_attribute(nutritional_info)
        self.ingredients = ingredients if ingredients is not None else []
        self.recipe = recipe if recipe is not None else {}

    def __str__(self):
        return self.title
