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


class Fruit(Ingredient):
    def __init__(self, name, ingredientType, measurement, price=None):
        super().__init__(name, ingredientType, measurement, price)


class Vegetable(Ingredient):
    def __init__(self, name, ingredientType, measurement, price=None):
        super().__init__(name, ingredientType, measurement, price)


class Meat(Ingredient):
    def __init__(self, name, ingredientType, measurement, price=None):
        super().__init__(name, ingredientType, measurement, price)


class Spice(Ingredient):
    def __init__(self, name, ingredientType, measurement, price=None):
        super().__init__(name, ingredientType, measurement, price)


class Condiment(Ingredient):
    def __init__(self, name, ingredientType, measurement, price=None):
        super().__init__(name, ingredientType, measurement, price)


class Bread(Ingredient):
    def __init__(self, name, ingredientType, measurement, price=None):
        super().__init__(name, ingredientType, measurement, price)


class Dairy(Ingredient):
    def __init__(self, name, ingredientType, measurement, price=None):
        super().__init__(name, ingredientType, measurement, price)


class Seed(Ingredient):
    def __init__(self, name, ingredientType, measurement, price=None):
        super().__init__(name, ingredientType, measurement, price)


class Noodle(Ingredient):
    def __init__(self, name, ingredientType, measurement, price=None):
        super().__init__(name, ingredientType, measurement, price)


class Other(Ingredient):
    def __init__(self, name, ingredientType, measurement, price=None):
        super().__init__(name, ingredientType, measurement, price)


class Dough(Ingredient):
    def __init__(self, name, ingredientType, measurement, price=None):
        super().__init__(name, ingredientType, measurement, price)
