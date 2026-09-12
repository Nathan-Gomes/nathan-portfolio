"""Copy the completed research artifacts into the static portfolio website."""
import argparse
import base64
import json
import shutil
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("project", type=Path, help="Path to quant-investment-pipeline")
args = parser.parse_args()
site = Path(__file__).resolve().parents[1]
destination = site / "public/investment-analytics"
files = ["output/report.html", "output/notebook.html", "output/portfolio_summary.csv",
         "output/model_scores.csv", "output/forward_projection_bands.csv",
         "output/forward_projection_summary.csv", "output/forward_scenarios.png",
         "notebooks/portfolio_exploration.ipynb"]
for name in files:
    target = destination / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.project / name, target)
notebook = json.loads((args.project / files[-1]).read_text())
for cell in notebook["cells"]:
    for output in cell.get("outputs", []):
        png = output.get("data", {}).get("image/png")
        if png:
            (destination / "performance.png").write_bytes(base64.b64decode(png))
            print(f"Published report, notebook, CSVs and chart preview to {destination}")
            raise SystemExit(0)
raise ValueError("Notebook has no saved chart output")
