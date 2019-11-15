import unittest
from forecast import forecast
from infovis import info_vis

class MyTest(unittest.TestCase):
    def test_dates(self):
        self.assertEqual(info_vis.qry_cons_aggr(), '2016-11-30 23:59:59-03:00')


if __name__ == '__main__':
    unittest.main()
