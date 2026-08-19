# StockSense: Operations Runbook

## SSH Access to EC2

```powershell
ssh -i "stocksense-server.pem" ubuntu@YOUR_INSTANCE_PUBLIC_IP
```
Run this from the folder where your `.pem` key file lives (or provide the full path to it). Find the current public IP in the AWS Console → EC2 → Instances → `stocksense-server`.

⚠️ If you've allocated an Elastic IP (recommended — see below), this address never changes. If not, re-check the Console every time you stop/start the instance.

---

## Starting Everything Up

### 1. Local stack (Postgres, Airflow)
```powershell
cd stocksense
docker compose up -d --build
```
Verify:
```powershell
docker ps
```
Expect: `stocksense_postgres`, `airflow_postgres`, `airflow_webserver`, `airflow_scheduler` (plus `stocksense_api`/`stocksense_ui` if also running the full stack locally).

**Local URLs:**
| Service | URL |
|---|---|
| Airflow UI | http://localhost:8080 (login: `admin` / `admin`) |
| Local API docs | http://localhost:8000/docs |
| Local UI | http://localhost:8501 |

### 2. AWS EC2 (production API + UI + Postgres)

If the instance is stopped, start it in the AWS Console (EC2 → Instances → Instance State → Start).

SSH in (see above), then:
```bash
cd stocksense
docker compose -f docker-compose.prod.yml up -d
```
(Add `--build` only if you've pulled new code since the containers were last built.)

**Production URLs** (replace with your actual IP/Elastic IP):
| Service | URL |
|---|---|
| API docs | http://YOUR_INSTANCE_PUBLIC_IP:8000/docs |
| Dashboard | http://YOUR_INSTANCE_PUBLIC_IP:8501 |

### 3. Confirm the full loop is connected
- Airflow UI (localhost:8080) → trigger `daily_ingestion` manually → confirm `fetch_prices`, `fetch_news`, `score_sentiment`, `data_quality_check` all go green
- Dashboard (EC2 URL:8501) → refresh → confirm data displays without errors

---

## Shutting Everything Down

**Local:**
```powershell
docker compose down
```
(Only add `-v` if you deliberately want to wipe local Postgres/Airflow data.)

**EC2** — stop containers and/or stop the instance:
```bash
docker compose -f docker-compose.prod.yml down
```
Then, optionally, fully stop the instance in the AWS Console to avoid any compute charges outside free tier. (If you don't have an Elastic IP, expect a new public IP next start.)

---

## Updating the Deployed App (Code/Config Changes)

Two-track workflow — **code changes** flow through git; **secrets never do.**

### Code/config changes (compose files, Python, DAGs, etc.)
```powershell
# locally
git add .
git commit -m "..."
git push
```
```bash
# on EC2, via SSH
cd stocksense
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

### Secret changes (API keys, passwords, Airflow secret key)
`.env` is gitignored and will **never** be updated by `git pull` — it must be manually edited on every machine that needs it.
```bash
# on EC2, via SSH
cd stocksense
nano .env
# edit values, save (Ctrl+O, Enter, Ctrl+X)
```
**If you changed the Postgres password specifically**, updating `.env` alone is not enough — Postgres only reads `POSTGRES_PASSWORD` on a container's *first-ever* initialization of an empty volume. Since your data volume already exists, you must also update the password on the running database directly:
```bash
docker exec -it stocksense_postgres psql -U stocksense -d stocksense
```
```sql
ALTER USER stocksense WITH PASSWORD 'the_new_password_from_.env';
\q
```
Do this on **both** local and EC2 Postgres if the password changed in both places. Then restart:
```bash
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d --build
```

---

## After Any Fresh Clone on EC2 (or a New Server)

A full `git clone` does **not** bring over anything gitignored — `.env` and `ml/artifacts/` both need to be manually recreated every time.

1. `git clone https://github.com/YOUR_USERNAME/stocksense.git`
2. `cd stocksense`
3. Recreate `.env` manually (`nano .env`, paste real values)
4. Create the artifacts folder and confirm ownership before copying into it:
   ```bash
   mkdir -p ml/artifacts
   ls -la ml/artifacts   # should be owned by `ubuntu`, not root
   ```
   If ownership is wrong:
   ```bash
   sudo chown -R ubuntu:ubuntu ml/artifacts
   ```
5. From your **local machine**, copy the trained model files up:
   ```powershell
   scp -i "stocksense-server.pem" ml/artifacts/baseline_model.pkl ml/artifacts/scaler.pkl ubuntu@YOUR_INSTANCE_PUBLIC_IP:~/stocksense/ml/artifacts/
   ```
6. If the Postgres data volume is also fresh (new server, not just a re-clone), also run the app's `db.init_db` against it once, from your laptop with `DATABASE_URL` pointed at this server:
   ```powershell
   python -m db.init_db
   ```
7. Bring the stack up:
   ```bash
   docker compose -f docker-compose.prod.yml up -d --build
   ```

---

## Elastic IP (Recommended One-Time Setup)

Without this, stopping/starting the EC2 instance assigns a new public IP each time, breaking every hardcoded reference (local Airflow's `DATABASE_URL`, bookmarked URLs, this doc). To fix permanently:

AWS Console → EC2 → **Elastic IPs** → Allocate new address → Actions → **Associate** → select `stocksense-server`.

Free as long as it stays attached to a running instance. Update all URLs/connection strings in this doc and your `.env` files to the Elastic IP once, and it never needs to change again.

---

## Quick Troubleshooting Checklist

- [ ] Did the EC2 public IP change (no Elastic IP set up)? Update `.env` and any hardcoded references.
- [ ] Is Docker Desktop actually running locally? Check the whale icon in the system tray.
- [ ] Does `docker ps` / `docker compose ... ps` show every expected container as `Up`/`healthy`, not restarting in a loop?
- [ ] UI shows no data / a 500 error: check `/health` and `/prices/AAPL` directly at the API docs URL first, to isolate API vs. UI vs. database.
- [ ] Just rotated a password? Did you also run `ALTER USER` against the **running** database, not just update `.env`?
- [ ] Just did a fresh `git clone` on EC2? Did you recreate `.env` **and** re-`scp` `ml/artifacts/*.pkl` — neither comes from git.
- [ ] Prediction endpoint 500s specifically: check `ml/artifacts/baseline_model.pkl` and `scaler.pkl` actually exist on that machine (`ls -la ml/artifacts`).
- [ ] Airflow task suddenly `ModuleNotFoundError`: check the new folder is mounted as a volume in `docker-compose.yml` for both `airflow-webserver` and `airflow-scheduler`.
- [ ] Airflow task hangs/fails with no clear reason: check `docker compose logs -f airflow-scheduler` for the real traceback before assuming.

---

## Secrets Currently in Rotation-Sensitive Use

A reminder of what's actually sensitive and needs to stay in sync across local `.env` and EC2 `.env`:
- `POSTGRES_PASSWORD` — also requires `ALTER USER` on both running databases when changed
- `AIRFLOW_SECRET_KEY`
- `NEWS_API_KEY` — rotate at [newsapi.org](https://newsapi.org) account settings
- `GEMINI_API_KEY` — rotate at [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
- `DATABASE_URL` — full connection string; update if host, user, or password changes
