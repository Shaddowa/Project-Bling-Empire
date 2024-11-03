import os
from abc import ABC, abstractmethod


class Measurement(ABC):
    def __init__(self, amount, unit):
        self.amount = amount
        self.unit = unit


class Ingredient(ABC):
    def __init__(self, name, ingredientType, measurement, price=None):
        self.name = name
        self.ingredientType = ingredientType
        self.measurement = measurement
        self.price = price

        self._category = self.__class__.__name__.lower()
        self.ean_products_path = f"""context/planing/meals/main/ean_products/{self._category}/{self.name.lower()}"""

        if Ingredient.check_ean_path_exists(self):
            pass
        else:
            pass  # TODO: Implement a method to create the path and check the prices
            # print(f"Path {self.ean_products_path} does not exist")

    def check_ean_path_exists(self):
        if os.path.exists(self.ean_products_path):
            return True
        return False


class Fruit(Ingredient):
    PINEAPPLE = "pineapple"

    def __init__(self, name, ingredientType, measurement, price=None):
        super().__init__(name, ingredientType, measurement, price)


class Vegetable(Ingredient):
    BELL_PEPPER = "bell pepper"
    RED_BELL_PEPPER = "red bell pepper"
    GREEN_BELL_PEPPER = "green bell pepper"
    RED_ONION = "red onion"
    GREEN_ONION = "green onion"
    CILANTRO = "cilantro"
    BIBB_LETTUCE_LEAVES = "bibb lettuce leaves"
    PERSIAN_CUCUMBER = "persian cucumber"
    BROCCOLI_OR_RADISH_SPROUTS = "broccoli or radish sprouts"
    PORTOBELLO_MUSHROOM_CAPS = "portobello mushroom caps"
    MUSHROOM = "mushroom"
    AVOCADO = "avocado"
    CILANTRO_LEAVES = "cilantro leaves"
    RADISH = "radish"
    BASIL_LEAVES = "basil leaves"
    HEIRLOOM_TOMATO = "heirloom tomato"
    CHERRY_TOMATO = "cherry tomato"
    SHALLOT = "shallot"
    BABY_ARUGULA = "baby arugula"
    YELLOW_ONION = "yellow onion"
    CELERY = "celery"
    CARROT = "carrot"
    BIB_BUTTER_OR_ROMAINE_LETTUCE = "bib, butter, or romaine lettuce"
    BOK_CHOY = "bok choy"
    ZUCCHINI = "zucchini"
    SCALLION = "scallion"
    JALAPENO = "jalapeño"  # Appears under both 'spice' and 'vegetable'
    PURPLE_CABBAGE = "purple cabbage"

    def __init__(self, name, ingredientType, measurement, price=None):
        super().__init__(name, ingredientType, measurement, price)


class Meat(Ingredient):
    PORK_LOIN = "pork loin"
    SALMON_FILLET = "salmon fillet"
    CHICKEN_THIGH = "chicken thigh"
    SEAFOOD = "seafood"
    CHICKEN_BREAST = "chicken breast"
    GROUND_CHICKEN = "ground chicken"

    def __init__(self, name, ingredientType, measurement, price=None):
        super().__init__(name, ingredientType, measurement, price)


class Seasoning(Ingredient):  # New class
    SALT = "salt"
    KOSHER_SALT = "kosher salt"
    PEPPER = "pepper"
    GARLIC = "garlic"
    LIME_ZEST = "lime zest"
    LEMON_ZEST = "lemon zest"
    RED_PEPPER_FLAKES = "red pepper flakes"
    CHIPOTLE_CHILI_POWDER = "chipotle chili powder"
    CHIPOTLES_IN_ADOBO = "chipotles in adobo"
    GINGER = "ginger"  # Added

    def __init__(self, name, ingredientType, measurement, price=None):
        super().__init__(name, ingredientType, measurement, price)


class Sweetener(Ingredient):  # New class
    SUGAR = "sugar"
    HONEY = "honey"

    def __init__(self, name, ingredientType, measurement, price=None):
        super().__init__(name, ingredientType, measurement, price)


class Oil(Ingredient):  # New class
    AVOCADO_OIL = "avocado oil"
    OLIVE_OIL = "olive oil"
    SESAME_OIL = "sesame oil"
    CANOLA_OIL = "canola oil"

    def __init__(self, name, ingredientType, measurement, price=None):
        super().__init__(name, ingredientType, measurement, price)


class SauceVinegar(Ingredient):  # New class
    SOY_SAUCE = "soy sauce"
    MIRIN = "mirin"
    SAKE = "sake"
    RICE_VINEGAR = "rice vinegar"
    BARBECUE_SAUCE = "barbecue sauce"
    COCONUT_AMINOS = "coconut aminos"
    SRIRACHA_SAUCE = "sriracha sauce"  # Simplified name
    LIME_JUICE = "lime juice"
    LEMON_JUICE = "lemon juice"

    def __init__(self, name, ingredientType, measurement, price=None):
        super().__init__(name, ingredientType, measurement, price)


class Egg(Ingredient):  # New class
    EGG = "egg"

    def __init__(self, name, ingredientType, measurement, price=None):
        super().__init__(name, ingredientType, measurement, price)


class Bread(Ingredient):
    BRIOCHE_BUNS = "brioche buns"

    def __init__(self, name, ingredientType, measurement, price=None):
        super().__init__(name, ingredientType, measurement, price)


class Dairy(Ingredient):
    COTIJA_CHEESE = "cotija cheese"
    WHOLE_MILK_COTTAGE_CHEESE = "whole milk cottage cheese"
    PARMESAN = "parmesan"
    GREEK_YOGURT = "greek yogurt"

    def __init__(self, name, ingredientType, measurement, price=None):
        super().__init__(name, ingredientType, measurement, price)


class Seed(Ingredient):
    SESAME_SEEDS = "sesame seeds"

    def __init__(self, name, ingredientType, measurement, price=None):
        super().__init__(name, ingredientType, measurement, price)


class Noodle(Ingredient):
    RAMEN = "ramen"

    def __init__(self, name, ingredientType, measurement, price=None):
        super().__init__(name, ingredientType, measurement, price)


class Other(Ingredient):
    BROTH = "broth"
    WATER = "water"
    CHICKEN_BROTH = "chicken broth"
    CORNSTARCH = "cornstarch"
    TOMATO_PASTE = "tomato paste"
    GRAIN_FREE_TORTILLAS = "grain free tortillas"

    def __init__(self, name, ingredientType, measurement, price=None):
        super().__init__(name, ingredientType, measurement, price)


class Dough(Ingredient):
    CORN_TORTILLAS = "corn tortillas"
    WHOLE_WHEAT_PIZZA_DOUGH = "whole wheat pizza dough"

    def __init__(self, name, ingredientType, measurement, price=None):
        super().__init__(name, ingredientType, measurement, price)
