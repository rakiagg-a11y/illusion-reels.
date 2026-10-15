# Daily run: make 4 reels and schedule them on @opticpop

This file is the instruction set for the daily scheduled task.

## Schedule (Asia/Jerusalem time)

| Slot | Israel | Who it reaches                         |
|------|--------|----------------------------------------|
| 0    | 09:00  | Europe morning (UK 07:00, CET 08:00)   |
| 1    | 15:00  | Europe lunch, US East Coast morning    |
| 2    | 19:00  | Europe evening, US East Coast lunch    |
| 3    | 22:30  | US East afternoon, US West lunch       |

All four fall inside the 08:00–23:00 Israel window.

## Steps

1. Install deps if missing: `pip install --break-system-packages numpy pillow scipy`
   (ffmpeg must be on PATH).
2. For slot in 0..3:
   `python3 generate.py --style auto --slot <slot> --out videos/<YYYY-MM-DD>/reel<slot>.mp4`
   Each run writes `reel<slot>.json` with `full_caption`.
3. Delete video folders older than 14 days under `videos/`.
4. Commit and push to `main`.
5. Each video's public URL is
   `https://raw.githubusercontent.com/rakiagg-a11y/illusion-reels./main/videos/<YYYY-MM-DD>/reel<slot>.mp4`.
   Check that it returns HTTP 200 before scheduling.
6. Schedule each one with Metricool `createScheduledPost`, using:
   - blogId `7443198`
   - provider `instagram`, `instagramData.type` = `REEL`, `showReelOnFeed` = true
   - the `full_caption` as text
   - the slot time above, timezone `Asia/Jerusalem`
   - `autoPublish` = true
7. If any step fails, do not schedule a broken post. Report what failed.
