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
2. Pick 4 different objects from `pointcloud.OBJECTS`, avoiding the ones posted
   the previous day (see the latest folder under `videos/`).
3. Render each one (about 10 minutes each; run two at a time):
   `python3 generate.py --style pointspin --obj "<object>" --out videos/<YYYY-MM-DD>/reel<slot>.mp4`
   Each run writes `reel<slot>.json` with `full_caption`. Make sure the four
   captions don't open with the same words; re-run captions with another seed
   if needed (`captions.build("pointspin", obj, seed)`).
4. Delete video folders older than 14 days under `videos/` (Metricool keeps its own copy).
5. Commit and push to `main`.
6. Each video's public URL is
   `https://raw.githubusercontent.com/rakiagg-a11y/illusion-reels./main/videos/<YYYY-MM-DD>/reel<slot>.mp4`.
   Check that it returns HTTP 200 before scheduling.
7. Schedule each one with Metricool `createScheduledPost`, using:
   - blogId `7443198`
   - provider `instagram`, `instagramData.type` = `REEL`, `showReelOnFeed` = true
   - the `full_caption` as text
   - the slot time above, timezone `Asia/Jerusalem`
   - `autoPublish` = true
   - `instagramData.audioConfiguration.audioId` = a track from the list below,
     a different one for each slot, rotating so the same track isn't used two days running.
8. If any step fails, do not schedule a broken post. Report what failed.

## Music (Instagram commercial library, dark / cinematic)

| audioId            | Track                                   |
|--------------------|-----------------------------------------|
| 2354395608146627   | Black Knight – Sam Marshall             |
| 1143868916400625   | Spector – Sam Marshall                  |
| 290641658216199    | Nacht – Austin Woodward, Adam Griffith  |
| 540038253374475    | Laconia – Adam Griffith                 |
| 1638340322893480   | Bizarre Circumstances – Global Genius   |
| 1090923063181541   | Invincible – Giulio Cercato             |
| 534836465627737    | Midnight Dreamer – Giulio Cercato       |
| 2141116976274369   | Cosmic Disco Fever – Adam Griffith      |
