import os, pathlib
app_path = pathlib.Path(__file__).resolve().parents[1] / "app.py"
os.environ.pop("APPMANUEL_NO_MAIN", None)
from streamlit.testing.v1 import AppTest
at = AppTest.from_file(str(app_path), default_timeout=120)
at.run()
print("exceptions:", len(at.exception))
for e in at.exception:
    print(str(e.value)[:2000])
print("tabs:", len(at.get("tabs")))
for lbl, seq in (("error",at.error),("warning",at.warning)):
    for x in seq:
        print(f"[{lbl}] {str(x.value)[:600]}")
# check contains
s="".join([str(x.value) for x in at.get("markdown")])
print("contains About:", "PyPSA App" in s)
print("contains Grid2Poster:", "Grid2Poster" in s or "grid2poster" in s.lower())
print("contains Run", "Run & Optimize" in s or "Run" in s)
print("plotly", len(at.get("plotly_chart")))
print("APPTEST OK" if len(at.exception)==0 else "FAIL")
