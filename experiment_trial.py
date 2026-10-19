"""Dated four-account timing experiment. Planning/analysis only; no posting API."""
import argparse
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
import hashlib
import html
import json
from pathlib import Path
import random
from zoneinfo import ZoneInfo

import account_studio as studio

TZ = ZoneInfo('Asia/Jerusalem')
PHASES = (0, 3, 2, 1)
ACCOUNTS = {
    'opticpop': dict(brand_id=7443198, minute=30, styles=('depth_flip', 'tilted_pair')),
    'hypnotorium': dict(brand_id=7498748, minute=40, styles=('color_echo', 'face_flash')),
    'spiralium_': dict(brand_id=7498862, minute=50, styles=('mirror_flip', 'still_wobble')),
    'trustyoureyes_': dict(brand_id=7498890, minute=55, styles=('brainrot_spin',)),
}
MARKETS = ('UTC', 'Europe/London', 'Europe/Berlin', 'America/New_York', 'America/Los_Angeles', 'Asia/Kolkata')


def instant(local):
    naive = local.replace(tzinfo=None)
    if local.astimezone(timezone.utc).astimezone(TZ).replace(tzinfo=None) != naive:
        raise ValueError('nonexistent local time; regenerate a safe calendar')
    if local.replace(fold=0).utcoffset() != local.replace(fold=1).utcoffset():
        raise ValueError('ambiguous local time; adjust start date/time before activation')
    return local.astimezone(timezone.utc)


def build_plan(start, seed=20261020):
    if isinstance(start, str):
        start = date.fromisoformat(start)
    if type(start) is not date or type(seed) is not int or seed < 0:
        raise ValueError('start must be a date and seed a nonnegative integer')
    rows = []
    for account, config in ACCOUNTS.items():
        for d in range(31):
            current = start+timedelta(days=d)
            first_style = ((d % 4)//2+d//4) % 2
            for window in range(6):
                hour = 4*window+PHASES[d % 4]
                local = datetime(current.year, current.month, current.day, hour, config['minute'], tzinfo=TZ)
                utc = instant(local)
                styles = config['styles']
                mode = styles[(window+first_style) % len(styles)]
                rows.append(dict(slot_id=f'trial05-{start:%Y%m%d}-{account}-d{d+1:02}-s{window+1}',
                    account=account, brand_id=config['brand_id'], network='instagram', style=mode,
                    day=d+1, window=window, local_date=current.isoformat(), local_time=local.strftime('%H:%M'),
                    scheduled_at_local=local.isoformat(), scheduled_at_utc=utc.isoformat(),
                    market_times={zone:utc.astimezone(ZoneInfo(zone)).isoformat() for zone in MARKETS},
                    observation_due_utc={str(age):(utc+timedelta(hours=age)).isoformat() for age in (24,72,168)},
                    core_analysis=d<28, status='planned_only',
                    asset_id=None, sha256=None, qa_approved=False, provider_post_id=None,
                    scheduling_ready=False, queue_reconciled=False, production_brief=None))
    plan = dict(kind='monthly_timing_trial',version=1,start_date=start.isoformat(),
        end_date=(start+timedelta(days=30)).isoformat(),timezone='Asia/Jerusalem',days=31,core_days=28,
        seed=seed,accounts={k:dict(v,styles=list(v['styles'])) for k,v in ACCOUNTS.items()},
        requested_daily_per_account=6,total_slots=744,user_authorized_trial=True,
        start_date_status='candidate_pending_full_first_day_assets_and_queue_reconciliation',
        active=False,activated_at_utc=None,externally_scheduled_posts=0,
        primary_metric='median reach at 72h within account/style/four-hour local window',
        metric_age_tolerance_hours=[69,75],metrics_collector_active=False,
        sources_commit='25855d2757fa5f4772e8b60f1df7f702ca1fd5f8',
        excluded_optic_mode_not_removed='bistable_spin',
        structural_catalogue_note='Optic uses93 DepthFlip+93 original tilted-pair structures. 42 bistable parameter rows cannot provide62 monthly uniques.',
        slots=rows)
    plan['verification'] = verify_plan(plan)
    return plan


def verify_plan(plan):
    slots=plan['slots']
    if len(slots)!=744 or len({r['slot_id'] for r in slots})!=744:
        raise ValueError('requires744 unique slots')
    gaps={}
    for account, config in ACCOUNTS.items():
        group=[r for r in slots if r['account']==account]
        if len(group)!=186:
            raise ValueError('requires186 slots per account')
        times=sorted(datetime.fromisoformat(r['scheduled_at_utc']) for r in group)
        gaps[account]=min((b-a).total_seconds()/3600 for a,b in zip(times,times[1:]))
        if gaps[account]<3:
            raise ValueError('posts less than3 real hours apart')
        for day in range(1,32):
            daily=[r for r in group if r['day']==day]
            expected={m:6//len(config['styles']) for m in config['styles']}
            if len(daily)!=6 or dict(Counter(r['style'] for r in daily))!=expected:
                raise ValueError('daily style quota mismatch')
        for window in range(6):
            core=[r for r in group if r['day']<=28 and r['window']==window]
            expected={m:28//len(config['styles']) for m in config['styles']}
            if dict(Counter(r['style'] for r in core))!=expected:
                raise ValueError('core style/window balance mismatch')
        if set(Counter(r['local_time'] for r in group if r['day']<=28).values())!={7}:
            raise ValueError('core hour balance mismatch')
    final=max(datetime.fromisoformat(r['scheduled_at_utc']) for r in slots)
    return dict(passed=True,slots=744,per_account=186,core_style_window_count=14,
        trust_core_window_count=28,minimum_real_gap_hours=gaps,
        tentative_primary_analysis_at_local=(final+timedelta(hours=72)).astimezone(TZ).isoformat(),
        tentative_seven_day_followup_at_local=(final+timedelta(hours=168)).astimezone(TZ).isoformat(),
        final_analysis_rule='Use last actual included post+72h; all dates shift if activation changes.')


def attach_production(plan, approved=()):
    """Assign each existing approved clip once; others get unique local briefs.

    approved items must contain account, mode, path, sha256 and brief. No upload
    or schedule can be triggered here. TrustYourEyes is a Claude-owned task.
    """
    rng=random.Random(plan['seed'])
    used=set()
    pools=defaultdict(list)
    for item in approved:
        account,mode=item['account'],item['mode']
        if account not in ACCOUNTS or mode not in ACCOUNTS[account]['styles']:
            raise ValueError('approved asset outside allowed account styles')
        brief=studio.validate_brief(item['brief'])
        if brief['account']!=account or brief['mode']!=mode:
            raise ValueError('approved brief identity mismatch')
        path=Path(item['path'])
        if path.suffix.lower()!='.mp4' or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError('approved asset checksum mismatch')
        key=studio.structural_key(mode,brief['parameters'])
        if key in used:
            raise ValueError('duplicate approved concept')
        used.add(key); pools[account,mode].append(dict(item))
    for account, config in ACCOUNTS.items():
        if account=='trustyoureyes_':
            continue
        for mode in config['styles']:
            needed=sum(r['account']==account and r['style']==mode for r in plan['slots'])
            remaining=needed-len(pools[account,mode])
            briefs=studio.plan(account,remaining,plan['seed']%1_000_000,used,mode)['briefs'] if remaining else []
            for brief in briefs:
                used.add(studio.structural_key(mode,brief['parameters']))
                pools[account,mode].append(dict(brief=brief,path=None,sha256=None))
            # Existing approved clips remain first to prepare a small initial batch.
            ready=[x for x in pools[account,mode] if x['path']]
            pending=[x for x in pools[account,mode] if not x['path']]
            rng.shuffle(pending)
            pools[account,mode]=ready+pending
    for row in plan['slots']:
        if row['account']=='trustyoureyes_':
            row['status']='awaiting_claude_brainrot_production'
            row['production_owner']='Claude'
            continue
        item=pools[row['account'],row['style']].pop(0)
        b=item['brief']
        row.update(asset_id=b['id'],production_brief=b,sha256=item['sha256'],asset_path=item['path'],
            qa_approved=item['path'] is not None,
            status='approved_asset_pending_queue_and_audio' if item['path'] else 'awaiting_render_and_quality_review')
    plan['production_summary']=dict(unique_validated_python_briefs=558,
        existing_approved_assets=sum(r['qa_approved'] for r in plan['slots']),
        pending_claude_brainrot_tasks=186,
        awaiting_render_and_quality_review=sum(r['status']=='awaiting_render_and_quality_review' for r in plan['slots']),
        full_first_day_ready=all(r['qa_approved'] and r['queue_reconciled'] for r in plan['slots'] if r['day']==1))
    return plan


def review_html(plan):
    # Embedded data is local scheduling metadata; never fetches remote content.
    data=json.dumps([{k:r[k] for k in ('slot_id','account','style','day','window','local_date','local_time',
        'scheduled_at_utc','market_times','status','qa_approved')} for r in plan['slots']],ensure_ascii=True).replace('<','\\u003c')
    return '''<!doctype html><html lang="he" dir="rtl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>ניסוי שעות — חודש</title><style>body{font:16px Arial;background:#0b1020;color:#edf3ff;margin:30px;line-height:1.6}
    select{padding:10px;font:inherit}a{color:#88c9ff}.note{padding:16px;background:#263247;border-radius:12px}
    table{width:100%;border-collapse:collapse;margin-top:20px}td,th{padding:10px;border-bottom:1px solid #33415d;text-align:right}
    .ready{color:#a7efbc}.pending{color:#ffca87}h1{font-size:28px}</style>
    <h1>31 ימי ניסוי · 6 סרטונים ביום לכל חשבון</h1>
    <p class="note">התוכנית מתוארכת ל־'''+plan['start_date']+''' עד '''+plan['end_date']+'''. זהו תאריך מועמד, ולא תור שהופעל ב־Metricool.
    נדרשים 744 סרטונים; כרגע יש רק חמש דוגמאות מאושרות. 28 ימים הם ליבה מאוזנת ועוד 3 ימי הרחבה.
    כל שעות הפרסום בטבלה הן שעון ישראל; אפשר להשוות זמני מדינות. אין טענה שהן כבר שעות השיא של הקהל.</p>
    <label>חשבון <select id="account">'''+''.join('<option>'+a+'</option>' for a in ACCOUNTS)+'''</select></label>
    <label> הצגת זמן נוספת <select id="zone">'''+''.join('<option>'+z+'</option>' for z in MARKETS)+'''</select></label>
    <p><a href="plan.json">תוכנית JSON ותדריכי הפקה</a> · <a href="PROTOCOL_HE.md">פרוטוקול הניסוי</a> · <a href="REQUEST_FOR_CLAUDE_HE.txt">עדכון לקלאוד</a></p>
    <table><thead><tr><th>יום</th><th>תאריך</th><th>שעה בישראל</th><th>סגנון</th><th>אזור זמן נוסף</th><th>מצב חומרי גלם</th></tr></thead><tbody id="rows"></tbody></table>
    <script>const data='''+data+'''; const account=document.getElementById('account'),zone=document.getElementById('zone');
    function render(){document.getElementById('rows').innerHTML=data.filter(r=>r.account===account.value).map(r=>
    `<tr><td>${r.day}${r.day>28?' · הרחבה':''}</td><td>${r.local_date}</td><td>${r.local_time}</td><td>${r.style}</td><td dir="ltr">${r.market_times[zone.value]}</td><td class="${r.qa_approved?'ready':'pending'}">${r.qa_approved?'דוגמה מאושרת; טרם שובצה':'נדרש סרטון ובדיקת איכות'}</td></tr>`).join('');}
    account.onchange=zone.onchange=render;render();</script></html>'''


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('command',choices=('plan','analyze'))
    ap.add_argument('--out',required=True)
    ap.add_argument('--start',help='candidate YYYY-MM-DD, only with plan')
    ap.add_argument('--approved-assets',help='local JSON list with validated briefs, paths and approved checksums')
    ap.add_argument('--plan',help='existing plan JSON for analyze')
    ap.add_argument('--snapshots',help='JSON list of measured metric snapshots')
    a=ap.parse_args()
    try:
        target=Path(a.out)
        if target.exists():
            raise ValueError('choose a new output path')
        if a.command=='plan':
            if not a.start:
                raise ValueError('--start is required')
            plan=attach_production(build_plan(a.start),json.loads(Path(a.approved_assets).read_text(encoding='utf-8')) if a.approved_assets else [])
            target.mkdir(parents=True)
            studio.atomic_json(target/'plan.json',plan)
            (target/'review.html').write_text(review_html(plan),encoding='utf-8')
        else:
            from trial_metrics import analyze
            if not a.plan or not a.snapshots:
                raise ValueError('--plan and --snapshots required')
            report=analyze(json.loads(Path(a.plan).read_text(encoding='utf-8')),json.loads(Path(a.snapshots).read_text(encoding='utf-8')))
            target.parent.mkdir(parents=True,exist_ok=True)
            studio.atomic_json(target,report)
        print(str(target.resolve()))
    except (ValueError,OSError,KeyError) as e:
        ap.error(str(e))


if __name__=='__main__':
    main()
