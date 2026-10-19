from collections import Counter
from datetime import datetime
import unittest

import experiment_trial as trial


class TimingTrialTests(unittest.TestCase):
    def test_month_is_dated_balanced_and_handles_dst(self):
        plan=trial.build_plan('2026-10-20',days=31)
        self.assertEqual(plan['end_date'],'2026-11-19')
        self.assertEqual(len(plan['slots']),744)
        self.assertEqual(plan['verification']['minimum_real_gap_hours'],{a:3 for a in trial.ACCOUNTS})
        self.assertEqual(plan['verification']['tentative_primary_analysis_at_local'],'2026-11-22T22:55:00+02:00')
        for account in trial.ACCOUNTS:
            rows=[r for r in plan['slots'] if r['account']==account]
            self.assertEqual(Counter(r['local_date'] for r in rows),{r['local_date']:6 for r in rows})
            for r in rows:
                local=datetime.fromisoformat(r['scheduled_at_local'])
                utc=datetime.fromisoformat(r['scheduled_at_utc'])
                self.assertEqual(local.timestamp(),utc.timestamp())
                self.assertEqual(r['market_times']['America/New_York'],utc.astimezone(trial.ZoneInfo('America/New_York')).isoformat())
        optic=[r for r in plan['slots'] if r['account']=='opticpop']
        self.assertEqual(Counter(r['style'] for r in optic),{'depth_flip':93,'tilted_pair':93})

    def test_production_has558_distinct_briefs_and186_claude_tasks(self):
        plan=trial.attach_production(trial.build_plan('2026-10-20',days=31))
        briefs=[r['production_brief'] for r in plan['slots'] if r['production_brief']]
        keys=[trial.studio.structural_key(b['mode'],b['parameters']) for b in briefs]
        self.assertEqual(len(set(keys)),558)
        self.assertEqual(sum(r['status']=='awaiting_claude_brainrot_production' for r in plan['slots']),186)
        self.assertFalse(plan['active'])
        self.assertFalse(any(r['scheduling_ready'] or r['provider_post_id'] for r in plan['slots']))
        self.assertFalse(plan['production_summary']['full_first_day_ready'])

    def test_invalid_inputs_and_corrupt_slots_fail(self):
        for value in ('bad-date',True):
            with self.assertRaises(ValueError):
                trial.build_plan(value)
        plan=trial.build_plan('2026-10-20');plan['slots'][1]['slot_id']=plan['slots'][0]['slot_id']
        with self.assertRaises(ValueError):
            trial.verify_plan(plan)
        with self.assertRaises(ValueError):
            trial.attach_production(trial.build_plan('2026-10-20'),[dict(account='foreign',mode='bad')])

    def test_claude_thirty_day_table_scope(self):
        plan=trial.build_plan('2026-10-20')
        self.assertEqual(plan['days'],30)
        self.assertEqual(plan['end_date'],'2026-11-18')
        self.assertEqual(len(plan['slots']),720)
        self.assertEqual(plan['total_network_publications'],2160)
        for account in trial.ACCOUNTS:
            rows=[r for r in plan['slots'] if r['account']==account]
            self.assertEqual(len(rows),180)
            hours=Counter(int(r['local_time'][:2]) for r in rows)
            self.assertEqual(set(hours),set(range(24)))
            self.assertTrue(all(7<=count<=8 for count in hours.values()))
        self.assertFalse(any('brainana' in r['account'].lower() for r in plan['slots']))


if __name__=='__main__':
    unittest.main()
