import copy
from datetime import datetime, timedelta, timezone
import unittest
from zoneinfo import ZoneInfo

import trial_metrics as t


NOW = '2026-12-01T00:00:00Z'
TZ = ZoneInfo('Asia/Jerusalem')


def slot(day=1, window=2, account='hypnotorium', style='color_echo'):
    local = datetime(2026, 10, 20, 8, 40, tzinfo=TZ) + timedelta(days=day-1)
    local = local.replace(hour=window*4)
    return dict(slot_id=f'{account}-{day}-{window}', account=account, style=style,
                day=day, window=window, scheduled_at_utc=local.astimezone(timezone.utc).isoformat())


def plan(*slots):
    return dict(kind='monthly_timing_trial', version=1, timezone='Asia/Jerusalem',
                core_days=28, days=31, slots=list(slots))


def snapshot(s, age=72, delay=0, **metrics):
    actual = datetime.fromisoformat(s['scheduled_at_utc']) + timedelta(minutes=delay)
    as_of = actual + timedelta(hours=age)
    row = dict(slot_id=s['slot_id'], instagram_media_id='ig-'+s['slot_id'],
               actual_published_at_utc=actual.isoformat(), observed_at_utc=as_of.isoformat(),
               metrics_as_of_utc=as_of.isoformat(), reach=100, views=150, likes=4,
               comments=1, shares=2, saves=3)
    row.update(metrics)
    return row


class TrialMetricsTests(unittest.TestCase):
    def test_missing_source_time_and_missing_metrics_are_not_zero(self):
        a, b, c = slot(1), slot(2), slot(3)
        rows = [snapshot(a, metrics_as_of_utc=None),
                snapshot(b, reach=None, shares=None), snapshot(c, reach=0)]
        report = t.analyze(plan(a,b,c), rows, NOW)
        group = report['groups'][0]
        self.assertEqual(report['coverage']['strict_age_matched_slots'], 2)
        self.assertEqual(report['coverage']['snapshots_missing_as_of'], 1)
        self.assertEqual(group['median_reach'], 0)
        self.assertEqual(group['missing_reach'], 1)
        self.assertEqual(group['zero_reach'], 1)
        self.assertEqual(group['metric_available_n']['views'], 2)
        self.assertIsNone(group['rates']['shares']['median_per_1000_reached'])
        self.assertIsNone(group['rates']['total_engagement']['median_per_1000_reached'])

    def test_closest_age_not_highest_result_and_duplicate_is_single_observation(self):
        s=slot(); early=snapshot(s,69,reach=9999); chosen=snapshot(s,72,reach=80)
        late=snapshot(s,75,reach=99999)
        report=t.analyze(plan(s),[late,early,chosen,copy.deepcopy(chosen)],NOW)
        self.assertEqual(report['groups'][0]['median_reach'],80)
        self.assertEqual(report['groups'][0]['reach_n'],1)
        self.assertEqual(report['coverage']['duplicate_snapshots'],1)
        self.assertEqual(t.analyze(plan(s),[early,late],NOW)['groups'][0]['median_reach'],9999)

    def test_age_uses_source_timestamp_not_retrieval_time(self):
        s=slot(); stale=snapshot(s,72)
        actual=datetime.fromisoformat(stale['actual_published_at_utc'])
        stale['metrics_as_of_utc']=(actual+timedelta(hours=20)).isoformat()
        report=t.analyze(plan(s),[stale],NOW)
        self.assertEqual(report['coverage']['snapshots_outside_age_window'],1)
        self.assertEqual(report['groups'][0]['reach_n'],0)
        self.assertEqual(report['coverage']['observed_slots'],1)

    def test_impossible_and_future_times_rejected(self):
        s=slot(); good=snapshot(s)
        for field,value in [('actual_published_at_utc','2027-01-01T00:00:00Z'),
                            ('observed_at_utc','2027-01-01T00:00:00Z'),
                            ('metrics_as_of_utc','2026-10-19T00:00:00Z'),
                            ('metrics_as_of_utc','2026-11-29T00:00:00Z'),
                            ('observed_at_utc','2026-10-23T00:00:00')]:
            with self.subTest(field=field,value=value):
                bad=dict(good,**{field:value})
                with self.assertRaises(ValueError):t.analyze(plan(s),[bad],NOW)

    def test_protocol_deviations_visible_and_excluded(self):
        a,b,c=slot(1),slot(2),slot(3,window=1)
        # Same broad window but >60min late; different window despite only21min early.
        rows=[snapshot(a,delay=61),snapshot(b),snapshot(c,delay=-41)]
        report=t.analyze(plan(a,b,c),rows,NOW)
        self.assertEqual(report['coverage']['protocol_deviation_slots'],2)
        self.assertEqual(sum(g['reach_n']for g in report['groups']),1)
        self.assertEqual(sum(g['age_matched_slots']for g in report['groups']),3)

    def test_core_and_extension_do_not_pool(self):
        a,b=slot(28),slot(29)
        report=t.analyze(plan(a,b),[snapshot(a,reach=10),snapshot(b,reach=999999)],NOW)
        self.assertEqual({g['cohort']:g['median_reach']for g in report['groups']},
                         {'core':10,'extension':999999})

    def test_accounts_never_pool_and_trust_only_when_present_in_plan(self):
        a=slot(); trust=slot(account='trustyoureyes_',style='brainrot_spin')
        with self.assertRaises(ValueError):t.analyze(plan(a),[snapshot(trust)],NOW)
        report=t.analyze(plan(a,trust),[snapshot(a,reach=1),snapshot(trust,reach=999)],NOW)
        self.assertEqual({g['account']:g['median_reach']for g in report['groups']},
                         {'hypnotorium':1,'trustyoureyes_':999})
        self.assertEqual(report['coverage']['by_account']['trustyoureyes_']['expected'],1)
        foreign=slot(account='brainanaaaa')
        with self.assertRaises(ValueError):t.analyze(plan(foreign),[],NOW)

    def test_counters_and_identity_conflicts_rejected(self):
        s=slot()
        for field,value in [('reach',True),('shares',-1),('likes',1.2),('comments','7')]:
            with self.subTest(field=field):
                with self.assertRaises(ValueError):t.analyze(plan(s),[snapshot(s,**{field:value})],NOW)
        row=snapshot(s)
        with self.assertRaises(ValueError):t.analyze(plan(s),[row,dict(row,reach=200)],NOW)
        with self.assertRaises(ValueError):t.analyze(plan(s),[row,dict(row,instagram_media_id='other')],NOW)
        other=slot(2)
        with self.assertRaises(ValueError):t.analyze(plan(s,other),[row,snapshot(other,instagram_media_id=row['instagram_media_id'])],NOW)

    def test_complete_and_partial_engagement_rates_are_distinct(self):
        a,b=slot(1),slot(2)
        report=t.analyze(plan(a,b),[snapshot(a,reach=100,shares=None),snapshot(b,reach=200)],NOW)
        rates=report['groups'][0]['rates']
        self.assertEqual(rates['shares']['n'],1)
        self.assertEqual(rates['shares_plus_saves']['median_per_1000_reached'],25)
        self.assertEqual(rates['total_engagement']['n'],1)
        self.assertEqual(rates['total_engagement']['median_per_1000_reached'],50)
        self.assertEqual(rates['likes']['n'],2)

    def test_recommendation_requires_counts_weekdays_comparison_and_uncertainty(self):
        slots=[slot(day,window)for day in range(1,15)for window in (1,2)]
        rows=[snapshot(s,reach=100)for s in slots]
        report=t.analyze(plan(*slots),rows,NOW)
        recommendation=report['recommendations'][0]
        self.assertEqual(recommendation['status'],'provisional_tie')
        self.assertEqual(recommendation['candidate_windows'],[1,2])
        self.assertTrue(recommendation['requires_confirmation_test'])
        self.assertFalse(report['publishing_enabled'])
        self.assertEqual(report,t.analyze(plan(*slots),list(reversed(rows)),NOW))
        sparse=slots[:8]
        self.assertEqual(t.analyze(plan(*sparse),[],NOW)['recommendations'][0]['status'],
                         'insufficient_comparable_data')

    def test_bad_contract_naive_schedule_and_date_day_disagreement_rejected(self):
        s=slot()
        for patch in [dict(version=True),dict(core_days=True),dict(timezone='UTC'),dict(days=29)]:
            bad=plan(s);bad.update(patch)
            with self.assertRaises(ValueError):t.analyze(bad,[],NOW)
        bad=dict(s,scheduled_at_utc='2026-10-20T08:40:00')
        with self.assertRaises(ValueError):t.analyze(plan(bad),[],NOW)
        with self.assertRaises(ValueError):t.analyze(plan(s,s),[],NOW)
        bad=slot(2);bad['day']=3
        with self.assertRaises(ValueError):t.analyze(plan(s,bad),[],NOW)

    def test_thirty_day_contract_has_180_slots_and_rejects_day31(self):
        slots=[slot(day,window)for day in range(1,31)for window in range(6)]
        monthly=plan(*slots);monthly['days']=30
        report=t.analyze(monthly,[snapshot(slots[-1],reach=321)],NOW)
        self.assertEqual(report['days'],30)
        self.assertEqual(report['coverage']['expected_slots'],180)
        self.assertEqual(sum(g['expected_slots']for g in report['groups']if g['cohort']=='core'),168)
        extension=[g for g in report['groups']if g['cohort']=='extension']
        self.assertEqual(sum(g['expected_slots']for g in extension),12)
        self.assertEqual(sum(g['reach_n']for g in extension),1)
        invalid=plan(slot(31));invalid['days']=30
        with self.assertRaises(ValueError):t.analyze(invalid,[],NOW)
        self.assertEqual(t.analyze(plan(slot(31)),[snapshot(slot(31))],NOW)['days'],31)


if __name__=='__main__':unittest.main()
