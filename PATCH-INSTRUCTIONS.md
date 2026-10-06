# LitRadar v0.4.0 → v0.4.1 patch

Copy the files in this archive over your existing v0.4.0 source tree. Do **not** replace:
- `data/litradar.sqlite3`
- `data/offline/`
- `.venv/`
- `.env`

Then run:

```powershell
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python cli.py init
pytest -q
```

No SQLite reset is required. The new `bibliography.py` and `offline.py` modules are additions; the other files are updated source/docs/tests.
