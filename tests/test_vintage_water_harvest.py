import unittest
from dataclasses import replace
from sommelier_v2.knowledge.vintage_engine import DailyWeather, VintageModelParams, simulate_vintage
from sommelier_v2.knowledge.vineyard_engine import VineyardBlock, VineyardEngine


class WaterHarvestTests(unittest.TestCase):
    def weather(self):
        return [DailyWeather(d, 14, 28, humidity_pct=90) for d in range(80, 240)]

    def test_irrigation_supplies_water_without_rain_disease(self):
        dry = simulate_vintage(self.weather(), harvest_day_of_year=225)
        watered = simulate_vintage([replace(d, irrigation_mm=6) for d in self.weather()], harvest_day_of_year=225)
        rainy = simulate_vintage([replace(d, rain_mm=6) for d in self.weather()], harvest_day_of_year=225)
        self.assertLess(watered.drought_stress, dry.drought_stress)
        self.assertEqual(watered.harvest_window_rain_mm, 0)
        self.assertEqual(watered.disease_pressure, dry.disease_pressure)
        self.assertGreater(rainy.disease_pressure, watered.disease_pressure)
        self.assertGreater(rainy.harvest_window_rain_mm, 0)

    def test_daily_water_mass_balance(self):
        params = VintageModelParams(initial_soil_water_mm=100)
        days = [replace(d, rain_mm=8, irrigation_mm=4) for d in self.weather()]
        result = simulate_vintage(days, params)
        previous = 100
        for weather, state in zip(days, result.daily_states):
            self.assertAlmostEqual(previous + weather.rain_mm + weather.irrigation_mm,
                                   state.soil_water_mm + state.drainage_mm + state.evapotranspiration_mm)
            previous = state.soil_water_mm

    def test_harvest_choice_changes_acid_and_excludes_later_storm(self):
        weather = [replace(d, rain_mm=20 if d.day_of_year >= 221 else 0) for d in self.weather()]
        early = simulate_vintage(weather, harvest_day_of_year=220)
        late = simulate_vintage(weather, harvest_day_of_year=235)
        self.assertEqual(early.harvest_day, 220)
        self.assertEqual(early.harvest_window_rain_mm, 0)
        self.assertGreater(late.harvest_window_rain_mm, 0)
        self.assertLess(late.acidity_retention_index, early.acidity_retention_index)
        self.assertEqual(early.daily_states[-1].day_of_year, 220)

    def test_block_irrigation_is_not_rain(self):
        block = VineyardBlock('b', 'Example', 1, 2000, 'France', 'Example', irrigation_mm_per_week=35)
        adjusted = VineyardEngine.__new__(VineyardEngine)._microclimate(block, [DailyWeather(100, 10, 20, rain_mm=2)])
        self.assertEqual(adjusted[0].rain_mm, 2)
        self.assertEqual(adjusted[0].irrigation_mm, 5)

    def test_missing_pick_date_and_invalid_weather_fail(self):
        with self.assertRaises(ValueError):
            simulate_vintage(self.weather(), harvest_day_of_year=300)
        for weather in ([DailyWeather(1, 20, 10)], [DailyWeather(1, 10, 20, irrigation_mm=-1)],
                        [DailyWeather(1, 10, 20)] * 2):
            with self.assertRaises(ValueError):
                simulate_vintage(weather)

    def test_weather_irrigation_cannot_bypass_block_restriction(self):
        block = VineyardBlock('b', 'Example', 1, 2000, 'France', 'Example', irrigation_allowed=False)
        with self.assertRaisesRegex(ValueError, "not allowed"):
            VineyardEngine.__new__(VineyardEngine).simulate(
                block, [DailyWeather(100, 10, 20, irrigation_mm=2)], vintage_year=2023)
