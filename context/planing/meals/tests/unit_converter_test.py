import unittest
from fractions import Fraction
from context.planing.meals.main.data_classes.ingredients import Measurement
from context.planing.meals.main.data_classes.unit import MeasurementUnit
from context.planing.meals.main.utils.unit_converter import UnitConverter


class TestUnitConverter(unittest.TestCase):

    def test_convert_cup_to_ml(self):
        # Test conversion of 2 cups to milliliters
        measurement = Measurement(2, MeasurementUnit.CUP)
        expected = Measurement(480, MeasurementUnit.ML)
        result = UnitConverter.convert(measurement)
        self.assertAlmostEqual(result.amount, expected.amount, places=1)
        self.assertEqual(result.unit, expected.unit)

    def test_convert_fraction_cup_to_ml(self):
        # Test conversion of a fractional cup (1/2 cup) to milliliters
        measurement = Measurement(Fraction(1, 2), MeasurementUnit.CUP)
        expected = Measurement(120, MeasurementUnit.ML)
        result = UnitConverter.convert(measurement)
        self.assertAlmostEqual(result.amount, expected.amount, places=1)
        self.assertEqual(result.unit, expected.unit)

    def test_convert_str_fraction_cup_to_ml(self):
        # Test conversion of a string fraction ("1/4") cup to milliliters
        measurement = Measurement("1/4", MeasurementUnit.CUP)
        expected = Measurement(60, MeasurementUnit.ML)
        result = UnitConverter.convert(measurement)
        self.assertAlmostEqual(result.amount, expected.amount, places=1)
        self.assertEqual(result.unit, expected.unit)

    def test_convert_invalid_str_fraction(self):
        # Test conversion of an invalid string fraction, expecting a ValueError
        measurement = Measurement("invalid", MeasurementUnit.CUP)
        with self.assertRaises(ValueError):
            UnitConverter.convert(measurement)

    def test_convert_fl_oz_to_ml(self):
        # Test conversion of fluid ounces (3 fl oz) to milliliters
        measurement = Measurement(3, MeasurementUnit.FL_OZ)
        expected = Measurement(88.71, MeasurementUnit.ML)
        result = UnitConverter.convert(measurement)
        self.assertAlmostEqual(result.amount, expected.amount, places=2)
        self.assertEqual(result.unit, expected.unit)

    def test_convert_lb_to_grams(self):
        # Test conversion of pounds (1 lb) to grams
        measurement = Measurement(1, MeasurementUnit.LB)
        expected = Measurement(453.59, MeasurementUnit.GRAMS)
        result = UnitConverter.convert(measurement)
        self.assertAlmostEqual(result.amount, expected.amount, places=2)
        self.assertEqual(result.unit, expected.unit)

    def test_convert_oz_to_grams(self):
        # Test conversion of ounces (5 oz) to grams
        measurement = Measurement(5, MeasurementUnit.OZ)
        expected = Measurement(141.75, MeasurementUnit.GRAMS)
        result = UnitConverter.convert(measurement)
        self.assertAlmostEqual(result.amount, expected.amount, places=2)
        self.assertEqual(result.unit, expected.unit)

    def test_convert_unsupported_unit(self):
        # Test conversion of an unsupported unit, expecting a ValueError
        with self.assertRaises(ValueError):
            measurement = Measurement(1, "unsupported_unit")
            UnitConverter.convert(measurement)

    def test_convert_negative_value(self):
        # Test conversion of a negative value (-1 cup to milliliters)
        measurement = Measurement(-1, MeasurementUnit.CUP)
        expected = Measurement(-240, MeasurementUnit.ML)
        result = UnitConverter.convert(measurement)
        self.assertAlmostEqual(result.amount, expected.amount, places=1)
        self.assertEqual(result.unit, expected.unit)

    def test_convert_zero_value(self):
        # Test conversion of zero value (0 fluid ounces to milliliters)
        measurement = Measurement(0, MeasurementUnit.FL_OZ)
        expected = Measurement(0, MeasurementUnit.ML)
        result = UnitConverter.convert(measurement)
        self.assertEqual(result.amount, expected.amount)
        self.assertEqual(result.unit, expected.unit)

    def test_convert_large_lb_to_grams(self):
        # Test conversion of a large value (10000 lb) to grams
        measurement = Measurement(10000, MeasurementUnit.LB)
        expected = Measurement(4535.92, MeasurementUnit.KG)
        result = UnitConverter.convert(measurement)
        print(result.unit)
        print(result.amount)
        print(expected.unit)
        print(expected.amount)

        self.assertAlmostEqual(result.amount, expected.amount, places=1)
        self.assertEqual(result.unit, expected.unit)

    def test_convert_small_cup_to_ml(self):
        # Test conversion of a very small value (0.001 cups) to milliliters
        measurement = Measurement(0.001, MeasurementUnit.CUP)
        expected = Measurement(0.24, MeasurementUnit.ML)
        result = UnitConverter.convert(measurement)
        self.assertAlmostEqual(result.amount, expected.amount, places=2)
        self.assertEqual(result.unit, expected.unit)



if __name__ == '__main__':
    unittest.main()
