import unittest
import os
from unittest.mock import patch
from pathlib import Path
from streamlit.testing.v1 import AppTest

class DashboardTests(unittest.TestCase):
    @patch.dict(os.environ, {"OPENAI_API_KEY": ""})
    def test_results_open_directly_and_scenario_recalculates(self):
        app = Path(__file__).parents[1]/'app.py'
        at = AppTest.from_file(str(app),default_timeout=30).run()
        self.assertFalse(at.exception,[x.message for x in at.exception])
        self.assertEqual(len(at.date_input),0)
        self.assertEqual(len(at.radio),0)
        self.assertEqual(len(at.get('file_uploader')),0)
        self.assertEqual([tab.label for tab in at.tabs],['Overview','All locations & results'])
        self.assertEqual(at.metric[1].value,'1,308')
        at.slider[0].set_value(0).run()
        self.assertFalse(at.exception,[x.message for x in at.exception])
        baseline = next(m for m in at.metric if m.label=='Simulated median wait').value
        self.assertEqual(baseline,'71.2 min')
        at.slider[0].set_value(5).run()
        self.assertEqual(next(m for m in at.metric if m.label=='Simulated median wait').value,'5.5 min')
        at.text_input[0].set_value('DCU Collins Avenue').run()
        self.assertFalse(at.exception,[x.message for x in at.exception])
        self.assertEqual(at.metric[0].value,'595')
        self.assertEqual(len(at.dataframe[2].value),3)
        self.assertIn('DCU Collins Avenue',at.selectbox[1].format_func(at.selectbox[1].value))
        at.button[0].click().run()
        self.assertTrue(any('not connected yet' in x.value for x in at.info))

if __name__ == '__main__':
    unittest.main()

