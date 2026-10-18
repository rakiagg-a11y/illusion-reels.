# Daily run: make 4 reels and schedule them on @opticpop

This file is the instruction set for the daily scheduled task.

## Schedule (Asia/Jerusalem time)

| Slot | Israel | Who it reaches                         |
|------|--------|----------------------------------------|
| 0    | 08:50  | Europe morning (UK 07:00, CET 08:00)   |
| 1    | 14:50  | Europe lunch, US East Coast morning    |
| 2    | 18:50  | Europe evening, US East Coast lunch    |
| 3    | 22:20  | US East afternoon, US West lunch       |

Scheduled 10 minutes before the target hour (09:00 / 15:00 / 19:00 / 22:30)
because upload + processing takes ~5–10 minutes. All inside 08:00–23:00 Israel.

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
   `https://raw.githubusercontent.com/rakiagg-a11y/illusion-reels./<commit-sha>/videos/<YYYY-MM-DD>/reel<slot>.mp4`
   (use the pushed commit's SHA, not `main`: GitHub caches `main` for a few minutes,
   so a re-rendered file could otherwise be fetched in its old version).
   Check that it returns HTTP 200 before scheduling.
7. Schedule each reel as TWO Metricool posts (`createScheduledPost`, blogId `7443198`,
   same video URL, same `full_caption` text, same slot time, timezone `Asia/Jerusalem`):
   - **Facebook, automatic:** providers `[{"network":"facebook"}]`,
     `facebookData.type` = `REEL`, `autoPublish` = true.
   - **Instagram, manual while the selected native audio is unverified:** use `short_caption` (a one-line hook
     that shows in full before "more", then the 5 hashtags hidden below it),
     providers `[{"network":"instagram"}]`,
     `instagramData.type` = `REEL`, `showReelOnFeed` = true, `autoPublish` = **false**,
     and NO `audioConfiguration`. Metricool sends Rakia a push notification at the slot
     time; she adds a trending song in the Instagram app and publishes.
8. If any step fails, do not schedule a broken post. Report what failed.

## Music

The current instructions add music by hand in the Instagram app. This is not a
blanket restriction on Creator accounts. Metricool now supports native Reel audio
for tracks authorized for third-party use, with a Facebook Login connection.
The user's priority is the selected trending sound, not a silent automatic post.
Before changing the manual route, follow [AUDIO_AUTOMATION.md](AUDIO_AUTOMATION.md)
and verify the exact sound against the actual brand. If unavailable or unverified,
hold the automatic route; do not substitute a different track or post silently.
The new preflight is read-only and does not activate or modify this daily job.

Songs the reference page uses most: Little Dark Age (MGMT), Coward (Hans Zimmer),
Gabriel (Felsmann + Tiley), Return to Sender (John Luther), Credits Song for My Death
(vivivivivi), Dark Fantasy (MPDV), Want To Love (Aloboi), around the world (slowed + reverb).

The list below is a historical selection of commercial-library track IDs. They
have not been revalidated for the current account; do not use them as automatic
fallbacks for the user's requested sound:

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
