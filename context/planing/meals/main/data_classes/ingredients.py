from abc import ABC, abstractmethod


class Ingredient(ABC):
    def __init__(self, name, price=None):
        self.name = name
        self.price = price


class Vegetable(Ingredient):
    pass


class Meat(Ingredient):
    pass


class Spice(Ingredient):
    pass


