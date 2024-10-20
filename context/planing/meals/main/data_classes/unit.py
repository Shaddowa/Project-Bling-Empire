from enum import Enum


class GeneralUnit(Enum):
    SMALL = "small"
    MEDIUM = "medium"
    WHOLE = "whole"
    HALF = "half"
    SLICES = "slices"
    CLOVES = "cloves"
    LEAVES = "leaves"
    PACKAGE = "package"
    PINCH = "pinch"
    CAN = "can"


class MeasurementUnit(Enum):
    CUP = "cup"
    TBSP = "tbsp"
    TSP = "tsp"
    OZ = "oz"
    FL_OZ = "fl_oz"
    LB = "lb"
    INCH = "inch"
    ML = "ml"
    DL = "dl"
    L = "l"
    KG = "kg"
    GRAMS = "grams"
