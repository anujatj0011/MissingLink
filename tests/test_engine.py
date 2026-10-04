import unittest
from datetime import date
import numpy as np
import pandas as pd
from engine import seconds, active_services, match, metrics, rank

class TransferTests(unittest.TestCase):
    def test_near_miss_and_shift(self):
        a = [seconds('17:29:00')]
        b = [seconds('17:25:00'),seconds('17:55:00')]
        base = match(a,b,0)
        self.assertEqual(base.wait.iloc[0],26)
        self.assertTrue(base.near_miss.iloc[0])
        self.assertEqual(match(a,b,0,5).wait.iloc[0],1)

    def test_buffer_and_equal_departure(self):
        self.assertEqual(match([100],[100,400],0).wait.iloc[0],0)
        self.assertEqual(match([100],[100,400],2).wait.iloc[0],5)

    def test_no_later_service_and_denominator(self):
        result = match([100,1000],[90,100],0)
        self.assertTrue(np.isnan(result.wait.iloc[1]))
        self.assertEqual(metrics(result,[90,100])['no_service'],1)
        self.assertEqual(len(match([100],[],0)),1)

    def test_service_day_and_exceptions(self):
        self.assertEqual(seconds('25:10:00'),90600)
        cal = pd.DataFrame([{'service_id':'weekday','start_date':'20260101','end_date':'20261231','monday':'1'}])
        exceptions = pd.DataFrame([{'service_id':'weekday','date':'20261005','exception_type':'2'},
                                   {'service_id':'special','date':'20261005','exception_type':'1'}])
        self.assertEqual(active_services(cal,exceptions,date(2026,10,5)),{'special'})


if __name__ == '__main__':
    unittest.main()
