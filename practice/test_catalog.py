from django.test import SimpleTestCase
from .questions import QUESTIONS, BY_ID
from .fixtures import dataset
from .judge import execute_sql


class ProductAnalyticsTests(SimpleTestCase):
    def test_ordered_funnel_rejects_reverse_and_equal_timestamps(self):
        for seed in (0, 7, 22):
            result = execute_sql(BY_ID['ordered-user-funnel']['solution'], (seed,))[0]
            self.assertEqual(result['columns'], ['user_id'])
            self.assertEqual(result['rows'], [[1]] if seed == 0 else [[1], [2]])

    def test_click_rate_handles_no_views_and_integrity_excludes_guests(self):
        rates = execute_sql(BY_ID['event-click-rate']['solution'])[0]
        self.assertIn(['tablet', None], rates['rows'])
        result = execute_sql(BY_ID['missing-customer-orders']['solution'], (0, 7, 22))
        self.assertEqual(result[0]['rows'], [])
        self.assertEqual(result[1]['rows'], [[21, 999]])
        self.assertEqual(result[2]['rows'], [[21, 999]])

    def test_count_distinct_is_not_event_count(self):
        result = execute_sql(BY_ID['unique-product-visitors']['solution'])[0]
        expected = {}
        for _, user, _, kind, device in dataset()['events']:
            if kind == 'view':
                expected.setdefault(device, set())
                if user is not None:
                    expected[device].add(user)
        self.assertEqual(result['rows'], [[device, len(users)] for device, users in sorted(expected.items())])
        self.assertEqual(len(QUESTIONS), 40)
