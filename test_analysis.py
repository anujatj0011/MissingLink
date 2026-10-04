"""Check that packaged real-feed results agree with on-demand simulation."""
import gzip
import json
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from engine import match,metrics

DATA = Path(__file__).parents[1]/'data'

class PreparedAnalysisTests(unittest.TestCase):
    def test_ranked_results_and_scenarios_match_real_timetables(self):
        poor = pd.read_csv(DATA/'poor-transfers.csv',dtype={'stop_id':str})
        options = pd.read_csv(DATA/'improvement-scenarios.csv')
        with gzip.open(DATA/'transfer-index.json.gz','rt',encoding='utf-8') as file:
            index = json.load(file)
        samples = pd.concat([poor.head(5),poor.sample(min(20,len(poor)),random_state=42)]).drop_duplicates('id')
        for row in samples.itertuples():
            at = index[row.stop_id]
            a = np.asarray(at[row.source]['arrivals'])
            start,end = (7*3600,10*3600) if row.period=='Morning' else (16*3600,19*3600)
            a = a[(a>=start)&(a<end)]
            b = np.asarray(at[row.target]['departures'])
            baseline = metrics(match(a,b,2),b)
            self.assertTrue(baseline['flagged'])
            self.assertAlmostEqual(row.median,baseline['median'])
            self.assertAlmostEqual(row.near_rate,baseline['near_rate'])
            for delta in [0,int(row.best_shift),10]:
                simulated = metrics(match(a,b,2,delta),b)
                prepared = options[(options.id==row.id)&(options['shift']==delta)].iloc[0]
                self.assertAlmostEqual(prepared['median'],simulated['median'])
                self.assertEqual(prepared.no_service,simulated['no_service'])
            self.assertEqual(len(options[options.id==row.id]),11)

if __name__ == '__main__':
    unittest.main()
