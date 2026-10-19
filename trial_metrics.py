"""Pure, non-publishing analysis of age-matched monthly Instagram observations."""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import hashlib
import random
from statistics import median
from zoneinfo import ZoneInfo

ACCOUNTS = frozenset(('opticpop', 'hypnotorium', 'spiralium_', 'trustyoureyes_'))
COUNTERS = ('reach', 'views', 'likes', 'comments', 'shares', 'saves')
TZ = ZoneInfo('Asia/Jerusalem')


def _time(value, field):
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if result.tzinfo is None or result.utcoffset() is None:
            raise ValueError()
        return result.astimezone(timezone.utc)
    except (AttributeError, TypeError, ValueError):
        raise ValueError(f'{field} must be an aware ISO timestamp') from None


def _integer(value, low, high, field):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f'invalid {field}')


def _interval(rows, seed):
    """Deterministic percentile bootstrap, resampling whole publication days."""
    by_day = defaultdict(list)
    for day, value in rows:
        by_day[day].append(value)
    days = sorted(by_day)
    if len(days) < 2:
        return None
    rng = random.Random(seed)
    estimates = sorted(median([v for d in rng.choices(days, k=len(days))
                               for v in by_day[d]]) for _ in range(1000))
    return [estimates[24], estimates[974]]


def analyze(plan, snapshots, now=None):
    """Validate observations, select one 69–75h snapshot/slot, and compare windows.

    Missing source timestamps never qualify as age-matched measurements. Source
    strings are data only. This function has no filesystem, network or side effects.
    """
    if not isinstance(plan, dict) or plan.get('kind') != 'monthly_timing_trial':
        raise ValueError('invalid plan kind')
    if (type(plan.get('version')) is not int or plan['version'] != 1 or
            plan.get('timezone') != 'Asia/Jerusalem' or
            type(plan.get('core_days')) is not int or plan['core_days'] != 28 or
            type(plan.get('days')) is not int or plan['days'] not in (30, 31)):
        raise ValueError('unsupported trial contract')
    if not isinstance(plan.get('slots'), list) or not isinstance(snapshots, list):
        raise ValueError('slots and snapshots must be lists')
    clock = datetime.now(timezone.utc) if now is None else _time(
        now.isoformat() if isinstance(now, datetime) else now, 'now')
    slots, calendar_keys, expected, origins = {}, set(), defaultdict(list), set()
    for slot in plan['slots']:
        if not isinstance(slot, dict):
            raise ValueError('invalid slot')
        sid, account, style = (slot.get(k) for k in ('slot_id', 'account', 'style'))
        if (not isinstance(sid, str) or not sid or sid in slots or
                not isinstance(account, str) or account not in ACCOUNTS):
            raise ValueError('invalid or duplicate slot/account')
        if not isinstance(style, str) or not style or len(style) > 100:
            raise ValueError('invalid style')
        _integer(slot.get('day'), 1, plan['days'], 'day')
        _integer(slot.get('window'), 0, 5, 'window')
        scheduled = _time(slot.get('scheduled_at_utc'), 'scheduled_at_utc')
        origins.add(scheduled.astimezone(TZ).date() - timedelta(days=slot['day'] - 1))
        if scheduled.astimezone(TZ).hour // 4 != slot['window']:
            raise ValueError('scheduled timestamp disagrees with window')
        key = account, slot['day'], slot['window']
        if key in calendar_keys:
            raise ValueError('duplicate account/day/window')
        calendar_keys.add(key)
        cohort = 'core' if slot['day'] <= 28 else 'extension'
        group = (cohort, account, style, slot['window'])
        slots[sid] = (slot, scheduled, group)
        expected[group].append(sid)
    if len(origins) > 1:
        raise ValueError('slot day disagrees with dated plan')
    candidates, submitted, slot_identity, media_slots = defaultdict(list), set(), {}, {}
    diagnostics = dict(snapshots_received=len(snapshots), snapshots_missing_as_of=0,
                       snapshots_outside_age_window=0, duplicate_snapshots=0)
    seen_snapshots = {}
    for row in snapshots:
        if not isinstance(row, dict) or row.get('slot_id') not in slots:
            raise ValueError('snapshot references an unknown slot')
        sid, mid = row['slot_id'], row.get('instagram_media_id')
        if not isinstance(mid, str) or not mid.strip():
            raise ValueError('instagram_media_id is required')
        actual = _time(row.get('actual_published_at_utc'), 'actual_published_at_utc')
        observed = _time(row.get('observed_at_utc'), 'observed_at_utc')
        if actual > observed or observed > clock:
            raise ValueError('publication/observation is impossible or in the future')
        identity = mid, actual
        if sid in slot_identity and slot_identity[sid] != identity:
            raise ValueError('conflicting media identity for slot')
        if mid in media_slots and media_slots[mid] != sid:
            raise ValueError('one Instagram media cannot belong to multiple slots')
        slot_identity[sid], media_slots[mid] = identity, sid
        values = {}
        for field in COUNTERS:
            value = row.get(field)
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError(f'{field} must be null or a nonnegative integer')
            values[field] = value
        submitted.add(sid)
        as_of = None if row.get('metrics_as_of_utc') is None else _time(
            row['metrics_as_of_utc'], 'metrics_as_of_utc')
        if as_of is not None and not actual <= as_of <= observed:
            raise ValueError('metrics source time must lie between publication and observation')
        snapshot_key = sid, mid, actual, observed, as_of
        metrics_key = tuple(values[k] for k in COUNTERS)
        if snapshot_key in seen_snapshots:
            if seen_snapshots[snapshot_key] != metrics_key:
                raise ValueError('conflicting counters for the same observation')
            diagnostics['duplicate_snapshots'] += 1
            continue
        seen_snapshots[snapshot_key] = metrics_key
        if as_of is None:
            diagnostics['snapshots_missing_as_of'] += 1
            continue
        age = (as_of - actual).total_seconds() / 3600
        if not 69 <= age <= 75:
            diagnostics['snapshots_outside_age_window'] += 1
            continue
        candidates[sid].append((abs(age - 72), as_of, observed, actual, age, values))
    selected, deviations = {}, []
    for sid, choices in candidates.items():
        # Age and source/capture time decide selection; metric values never do.
        choice = min(choices, key=lambda x: x[:3])
        _, as_of, observed, actual, age, values = choice
        slot, scheduled, _ = slots[sid]
        local = actual.astimezone(TZ)
        delay = (actual - scheduled).total_seconds() / 60
        deviates = (local.hour // 4 != slot['window'] or abs(delay) > 60 or
                    local.date() != scheduled.astimezone(TZ).date())
        selected[sid] = dict(metrics=values, age_hours=age, weekday=local.weekday(),
                             day=local.date().isoformat(), deviation=deviates)
        if deviates:
            deviations.append(dict(slot_id=sid, actual_window=local.hour // 4,
                                   delay_minutes=delay))
    groups = []
    for key, ids in sorted(expected.items()):
        cohort, account, style, window = key
        matched = [selected[s] for s in ids if s in selected]
        usable = [s for s in matched if not s['deviation']]
        reach_rows = [(s['day'], s['metrics']['reach']) for s in usable
                      if s['metrics']['reach'] is not None]
        weekdays = sorted({s['weekday'] for s in usable if s['metrics']['reach'] is not None})
        seed = int.from_bytes(hashlib.sha256(repr(key).encode()).digest()[:8], 'big')
        rates = {}
        for name, fields in [('shares', ('shares',)), ('saves', ('saves',)),
                             ('likes', ('likes',)), ('comments', ('comments',)),
                             ('shares_plus_saves', ('shares', 'saves')),
                             ('total_engagement', ('likes', 'comments', 'shares', 'saves'))]:
            values = [1000 * sum(s['metrics'][f] for f in fields) / s['metrics']['reach']
                      for s in usable if s['metrics']['reach'] not in (None, 0)
                      and all(s['metrics'][f] is not None for f in fields)]
            rates[name] = dict(n=len(values), median_per_1000_reached=median(values) if values else None)
        groups.append(dict(cohort=cohort, account=account, style=style, window=window,
            expected_slots=len(ids), observed_slots=sum(s in submitted for s in ids),
            age_matched_slots=len(matched), protocol_deviations=sum(s['deviation'] for s in matched),
            eligible_slots=len(usable), reach_n=len(reach_rows), weekday_coverage=weekdays,
            missing_reach=sum(s['metrics']['reach'] is None for s in usable),
            zero_reach=sum(s['metrics']['reach'] == 0 for s in usable),
            metric_available_n={f: sum(s['metrics'][f] is not None for s in usable) for f in COUNTERS},
            median_reach=median([v for _, v in reach_rows]) if reach_rows else None,
            reach_ci95=_interval(reach_rows, seed) if reach_rows else None, rates=rates))
    recommendations = []
    for account, style in sorted({(s['account'], s['style']) for s, _, _ in slots.values()}):
        qualified = sorted([g for g in groups if g['cohort'] == 'core' and
            g['account'] == account and g['style'] == style and g['reach_n'] >= 10 and
            len(g['weekday_coverage']) >= 4], key=lambda g: (-g['median_reach'], g['window']))
        tied = []
        if len(qualified) >= 2:
            top = qualified[0]
            tied = [g['window'] for g in qualified if g['reach_ci95'][1] >= top['reach_ci95'][0]]
        recommendations.append(dict(account=account, style=style,
            status=('provisional_tie' if len(tied) > 1 else 'provisional_candidate')
                   if tied else 'insufficient_comparable_data',
            candidate_windows=tied, qualified_window_count=len(qualified),
            requires_confirmation_test=True, automatic_settings_changed=False))
    return dict(kind='monthly_timing_report', version=1, publishing_enabled=False,
        days=plan['days'], core_days=28,
        primary='reach_at_72h_within_account_style_local_four_hour_window',
        capture_age_window_hours=[69, 75], bootstrap='1000 deterministic day-cluster percentile samples',
        coverage=dict(expected_slots=len(slots), observed_slots=len(submitted),
            slots_without_observations=len(slots)-len(submitted),
            strict_age_matched_slots=len(selected), slots_without_strict_snapshot=len(slots)-len(selected),
            protocol_deviation_slots=len(deviations),
            by_account={a: dict(expected=sum(s['account'] == a for s, _, _ in slots.values()),
                observed=sum(slots[s][0]['account'] == a for s in submitted),
                age_matched=sum(slots[s][0]['account'] == a for s in selected))
                for a in sorted({s['account'] for s, _, _ in slots.values()})}, **diagnostics),
        groups=groups, protocol_deviations=deviations, recommendations=recommendations,
        limitations=[f"Core28days and extension{plan['days'] - 28}days remain separate.",
            'Missing source age, reach or actions remain missing; views never replace reach.',
            'No inference of optimal minute, cross-account style causality or six/day versus three/day.'])
