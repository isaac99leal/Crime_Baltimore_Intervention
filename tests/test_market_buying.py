import unittest
from types import SimpleNamespace

from somm_simulator.models.market import quote_purchase, purchase_wine, weekly_offerings
from somm_simulator.models.restaurant import Restaurant


class MarketBuyingTests(unittest.TestCase):
    def wine(self, **kwargs):
        return SimpleNamespace(**({'id': 'wine-1', 'wholesale_cost': 20.0,
                                   'quantity_available': 30} | kwargs))

    def test_case_prices_include_freight(self):
        self.assertEqual(quote_purchase(20, 1).total, 32)
        self.assertEqual(quote_purchase(20, 6).total, 128.4)
        self.assertEqual(quote_purchase(20, 12).total, 228)
        self.assertEqual(quote_purchase(19.99, 6).wine_cost, 116.34)

    def test_invalid_quantities_and_prices(self):
        for qty in (0, -1, 1.5, True):
            with self.assertRaises(ValueError):
                quote_purchase(20, qty)
        for price in (-1, float('inf'), float('nan')):
            with self.assertRaises(ValueError):
                quote_purchase(price, 1)

    def test_purchase_updates_cash_stock_and_landed_cellar_cost(self):
        restaurant, wine = Restaurant(budget=1000), self.wine()
        purchase_wine(restaurant, wine, 6)
        purchase_wine(restaurant, wine, 12)
        self.assertAlmostEqual(restaurant.budget, 643.6)
        self.assertEqual(wine.quantity_available, 12)
        self.assertEqual(restaurant.cellar[0].quantity, 18)
        self.assertAlmostEqual(restaurant.cellar[0].purchase_price * 18, 356.4)
        self.assertAlmostEqual(restaurant.current_period.purchases, 356.4)

    def test_rejected_orders_change_nothing(self):
        for budget, capacity, stock in ((127, 100, 30), (1000, 5, 30), (1000, 100, 5)):
            restaurant = Restaurant(budget=budget, cellar_capacity=capacity)
            wine = self.wine(quantity_available=stock)
            with self.assertRaises(ValueError):
                purchase_wine(restaurant, wine, 6)
            self.assertEqual(restaurant.budget, budget)
            self.assertEqual(restaurant.cellar, [])
            self.assertEqual(restaurant.current_period.purchases, 0)
            self.assertEqual(wine.quantity_available, stock)

    def test_weekly_offers_cannot_be_rerolled_and_do_not_restock(self):
        wines = [self.wine(id=str(i)) for i in range(200)]
        first = weekly_offerings(wines, 1)
        self.assertEqual(first, weekly_offerings(list(reversed(wines)), 1))
        self.assertNotEqual(first, weekly_offerings(wines, 2))
        first[0].quantity_available = 0
        self.assertEqual(weekly_offerings(wines, 1)[0].quantity_available, 0)
        self.assertEqual(len(first), 120)


if __name__ == '__main__':
    unittest.main()
