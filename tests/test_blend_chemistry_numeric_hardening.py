from __future__ import annotations

import unittest

from sommelier_v2.knowledge.blend_chemistry import (
    BlendChemistryComponent,
    BlendChemistryConstraintError,
    BlendPostMixMeasurements,
    blend_chemistry,
)


class BlendChemistryNumericHardeningTests(unittest.TestCase):
    def test_boolean_and_numeric_string_inputs_fail_closed(self) -> None:
        for value in (True, False, "1.0"):
            with self.subTest(draw_l=value):
                with self.assertRaises(BlendChemistryConstraintError):
                    BlendChemistryComponent(source_id="lot", draw_l=value)  # type: ignore[arg-type]

        with self.assertRaises(BlendChemistryConstraintError):
            BlendChemistryComponent(source_id="lot", draw_l=1.0, ethanol_pct=True)  # type: ignore[arg-type]
        with self.assertRaises(BlendChemistryConstraintError):
            BlendPostMixMeasurements(ph="3.4")  # type: ignore[arg-type]

    def test_operation_oxygen_delta_must_be_real_numeric(self) -> None:
        component = BlendChemistryComponent(
            source_id="lot",
            draw_l=1.0,
            dissolved_oxygen_mg_l=1.0,
        )
        for value in (True, "0"):
            with self.subTest(operation_oxygen_delta_mg=value):
                with self.assertRaises(BlendChemistryConstraintError):
                    blend_chemistry(
                        (component,),
                        operation_oxygen_delta_mg=value,  # type: ignore[arg-type]
                    )


if __name__ == "__main__":
    unittest.main()
