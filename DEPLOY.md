# 🚀 Deploy PyPSA-App Streamlit — GitHub + Streamlit Cloud

**App:** `pypsa-app-streamlit` — 1131 lines, 9 tabs, 48h reference, synced Data Model ↔ Run, PyPSA 1.3.0 + HiGHS, Grid2Poster `us_mainland.geojson`  
**Zip:** `pypsa-app-streamlit.zip` (5.1 MB, 154 files, includes `pypsa-app/src`) — ready to unzip & push

---

## ✅ Quick Deploy (3 minutes, no CLI)

### 1) Create GitHub repo

1. Go to **https://github.com/new**
2. **Repository name:** `pypsa-app-streamlit` (or `pypsa-col`, `LICA_SE/pypsa-app-explorer`)
3. **Visibility:** Public (required for free Streamlit Cloud)
4. **Do NOT** check *Initialize with README* — you already have one
5. Click **Create repository**

### 2) Push this app (web upload — easiest, no git)

1. On the new repo page click **uploading an existing file**
2. **Drag & drop** the *unzipped* `pypsa-app-streamlit` folder **contents** (not the zip itself):
   ```
   app.py
   requirements.txt
   README.md
   DEPLOY.md
   assets/PyPSA-USA_network.png, assets/us_mainland.geojson, assets/user_reference_map.png
   pypsa-app/  (full clone with src/pypsa_app/backend/...)
   .streamlit/config.toml
   tools/test_app.py
   ```
   *Tip: if drag fails, use GitHub Desktop or `git` CLI below.*
3. Message: `deploy: PyPSA App 1131L 48h synced`
4. **Commit changes** → done, repo ready.

### Alternative: `git` CLI (if you have terminal)

```bash
# 1. Unzip
unzip pypsa-app-streamlit.zip
cd pypsa-app-streamlit

# 2. Init & push (replace <YOUR_GITHUB_USER> and <REPO>)
git init
git add .
git commit -m "deploy: PyPSA App 1131L 48h synced Data Model ↔ Run"
git branch -M main
git remote add origin https://github.com/<YOUR_GITHUB_USER>/pypsa-app-streamlit.git
git push -u origin main
# If using SSH:
# git remote add origin git@github.com:<YOUR_GITHUB_USER>/pypsa-app-streamlit.git
```

If you already have a repo (e.g. `srriverar/LICA_SE`), push there:
```bash
git remote add origin https://github.com/srriverar/LICA_SE.git
git push -u origin main  # or to a new branch: git push -u origin main:pypsa-app-streamlit
```

---

## ☁️ Deploy to Streamlit Cloud

1. Go to **https://share.streamlit.io** → **Sign in with GitHub**
2. **New app** → **Deploy a public app from GitHub**
   - **Repository:** `<YOUR_GITHUB_USER>/pypsa-app-streamlit`
   - **Branch:** `main`
   - **Main file path:** `app.py`  *(must be at repo root, not in subfolder)*
   - **App URL:** pick e.g. `pypsa-app-lica-se` → `https://pypsa-app-lica-se.streamlit.app`
3. **Advanced settings** → **Python version:** `3.13` (required, `pypsa>=1.3` + `pandas>=3.0` need ≥3.13)
4. Click **Deploy!** → Wait 2-4 min (installs `pypsa`, `highspy`, `linopy`, `xarray`, `netcdf4`, `plotly`, `streamlit`, `pydantic`, `sqlalchemy`, `fastapi`).

**First build logs** will show:
```
Using Python 3.13.X
pip install from requirements.txt ...
Streamlit 1.64.0
...
App started → https://<your-app>.streamlit.app
```

If you see `ResolutionImpossible pandas<3`, ensure `requirements.txt` has `pandas>=3.0` and `xarray>=2025.1.0` (already fixed in this zip).

### Streamlit Secrets (not needed for demo)

The demo uses **in-browser mock** `Postgres + Redis + Celery` (no real DB). For real `pypsa-app` backend you would add in **Streamlit Cloud → Settings → Secrets**:
```toml
DATABASE_URL = "postgresql://..."
REDIS_URL = "redis://..."
```

---

## 🧪 Test before deploy (local)

```bash
unzip pypsa-app-streamlit.zip
cd pypsa-app-streamlit
pip install -r requirements.txt
streamlit run app.py  # http://localhost:8501
# or test:
python tools/test_app.py  # → exceptions: 0, APPTEST OK
```

**Test the 48h sync:**
- `🗄️ Data Model → Build synthetic → 48h → Built ... synced`
- `▶️ Run & Optimize` → banner `🔗 Data Model synced — 30b 48h` → `Hours 48` → `🚀 Queue run` → `Optimal`
- `📊 Visualization → Source = Use last run` → dispatch **identical** to Run

---

## 🔧 What was fixed (for reviewers)

- `pd.options.future.infer_string=False` → fixes `HiGHS StringDtype` with `pandas 3.0 / xarray 2025.4`
- `mremove → remove` (pypsa 1.3), `duplicate key run-load → run-loading`, `IsADirectoryError schemas` → now lists `schemas/*.py`
- `🏗️ Architecture` now finds `src/pypsa_app/backend/api/routes` (11 files) & `models.py` via fresh `git clone`
- `48h horizon` as reference, `🗄️ Data Model = ▶️ Run = 📊 Visualization` (shared `st.session_state["dm-n"/"run-n"/"vis-n"]`)

---

## 📦 Zip contents

```
pypsa-app-streamlit/
├── app.py (1131L, 83K)
├── requirements.txt (streamlit, pandas>=3.0, pypsa, linopy, xarray, netcdf4, highspy, plotly...)
├── .streamlit/config.toml (theme #003366, headless)
├── README.md (clone-in-detail table)
├── DEPLOY.md (this file)
├── assets/ (PyPSA-USA_network.png 320K, us_mainland.geojson 395K, user_reference_map.png)
├── pypsa-app/ (full clone 9.3M, src/pypsa_app/backend/{main.py, models.py, api/routes, schemas, alembic})
└── tools/test_app.py
```

**Deploy URL after:** `https://<your-app>.streamlit.app` → share with `github.com/srriverar/LICA_SE`

*Prof. Sergio Rivera — LICA_SE (EMC-UN) — pypsacolombia initiative*
