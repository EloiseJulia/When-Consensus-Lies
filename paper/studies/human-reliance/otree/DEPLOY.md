# Deploy the study for free (public link)

The app is in `paper/studies/human-reliance/otree`. Data must persist, so we use a small
Postgres DB (free). Recommended host: **Render** (free web + free Postgres). Fly.io works too.

## Option A — Render (recommended, free)

1. Make sure this repo is on GitHub (it is).
2. Render.com -> **New +** -> **Blueprint** -> connect this repo. Render reads `render.yaml`
   (web service + free Postgres, env vars auto-set).
3. Wait for the build to finish. In **Environment**, copy the generated `OTREE_ADMIN_PASSWORD`.
4. Open **Shell** (Render dashboard) and run once (creates the DB tables):
   ```
   otree resetdb
   ```
   (Only the first time. Do NOT put this in the build command, or redeploys will wipe data.)
5. Your app is now at `https://reliance-xxxx.onrender.com`.

### Get the one participant link (participant view, no admin)
- Log in to `https://<yourapp>/` as `admin` / (the password from step 3).
- **Rooms -> reliance** -> copy the **participant URL** (room-wide link). Share THIS link.
  Each visitor is assigned a new participant and starts at the language page.
- (Alternative: **Sessions -> Create** a session of the config `reliance` with e.g. 200
  participants, then copy its **session-wide link** — same participant-first behavior.)

> Free web sleeps after ~15 min idle; the first visitor then waits ~30-60 s while it wakes.
> Fine for WeChat / email recruitment. Keep it warm before a batch by opening the link yourself.

## Option B — Fly.io (free allowances)
`fly launch` in the `otree` folder (it detects Python), add a free Postgres with
`fly postgres create`, set the same env vars (`OTREE_PRODUCTION=1`, `OTREE_AUTH_LEVEL=STUDY`,
`OTREE_ADMIN_PASSWORD`, `OTREE_SECRET_KEY`, `DATABASE_URL`), then `fly deploy`. Get the link the
same way (Rooms -> reliance).

## Notes
- Language (English / 简体中文) is chosen by the participant on the first page — one link serves both.
- Recruiting Chinese participants? A host reachable from China (a China-region VPS / Aliyun) loads
  faster there than Render; the app itself is identical.
- To download data: admin -> **Data** (or the app's custom export -> `reliance_custom.csv`), then run
  `python ../analysis/preregistered_analysis.py --data reliance_custom.csv`.
- If the free Postgres expires (~30 days), export your data before then.
