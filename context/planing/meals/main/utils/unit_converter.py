from fractions import Fraction
from context.planing.meals.main.data_classes.ingredients import Measurement
from context.planing.meals.main.data_classes.unit import MeasurementUnit


class UnitConverter:
    conversion_dict = {
        MeasurementUnit.CUP: 240,  # cups to milliliters
        MeasurementUnit.FL_OZ: 29.57,  # fluid ounces to milliliters
        MeasurementUnit.OZ: 28.35,  # ounces to grams
        MeasurementUnit.LB: 453.59,  # pounds to grams
        MeasurementUnit.INCH: 2.54  # inches to centimeters
    }

    @staticmethod
    def _convert_to_metric(amount, unit: MeasurementUnit):
        if isinstance(amount, Fraction):
            amount = float(amount)
        elif isinstance(amount, str):
            try:
                amount = float(Fraction(amount))
            except ValueError:
                raise ValueError(f"Invalid fraction format for amount: {amount}")

        if unit in UnitConverter.conversion_dict:
            return amount * UnitConverter.conversion_dict[unit]
        else:
            raise ValueError(f"Unit '{unit}' is not supported.")

    @staticmethod
    def _metric_conversion(amount, metric_unit: MeasurementUnit):
        """
        Handles metric conversions by scaling values based on thresholds.
        """
        if metric_unit == MeasurementUnit.ML:
            if amount >= 1000:
                return Measurement(amount / 1000, MeasurementUnit.L)
            elif amount >= 100:
                return Measurement(amount / 100, MeasurementUnit.DL)
            else:
                return Measurement(amount, MeasurementUnit.ML)
        elif metric_unit == MeasurementUnit.GRAMS:
            if amount >= 1000:
                return Measurement(amount / 1000, MeasurementUnit.KG)
            else:
                return Measurement(amount, MeasurementUnit.GRAMS)
        return Measurement(amount, metric_unit)

    @staticmethod
    def convert(measurement: Measurement):

        if measurement.unit in [
            MeasurementUnit.GRAMS,
            MeasurementUnit.KG,
            MeasurementUnit.ML,
            MeasurementUnit.L,
            MeasurementUnit.DL
        ]:
            return measurement

        amount, unit = measurement.amount, measurement.unit
        if unit in UnitConverter.conversion_dict:
            converted_amount = UnitConverter._convert_to_metric(amount, unit)
            if unit in [MeasurementUnit.TSP, MeasurementUnit.TBSP, MeasurementUnit.CUP, MeasurementUnit.FL_OZ]:
                return UnitConverter._metric_conversion(converted_amount, MeasurementUnit.ML)
            elif unit in [MeasurementUnit.OZ, MeasurementUnit.LB]:
                return UnitConverter._metric_conversion(converted_amount, MeasurementUnit.GRAMS)
            elif unit == MeasurementUnit.INCH:
                return Measurement(converted_amount, MeasurementUnit.INCH)  # Convert to centimeters
        else:
            raise ValueError(f"Unit '{unit}' is not supported.")
