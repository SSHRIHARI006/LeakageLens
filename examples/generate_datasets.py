from pathlib import Path
import numpy as np
import pandas as pd

rng = np.random.default_rng(42); out = Path("data"); out.mkdir(exist_ok=True)
def base(n=240):
    age = rng.normal(45, 12, n).round(1); spend = rng.normal(100, 30, n).round(1); y = ((age * .05 + spend * .02 + rng.normal(0, 1, n)) > 4.2).astype(int)
    return pd.DataFrame({"age": age, "spend": spend, "segment": rng.choice(["A", "B", "C"], n), "target": y})
clean = base(); clean.to_csv(out / "clean_classification.csv", index=False)
source = base(180)
dup = pd.concat([source, source.iloc[:45], source.iloc[45:90]], ignore_index=True); dup.to_csv(out / "duplicate_leakage.csv", index=False)
group = base(); group["customer_id"] = np.repeat(np.arange(80), 3); group.to_csv(out / "group_leakage.csv", index=False)
temporal = base(); temporal["event_date"] = pd.date_range("2023-01-01", periods=len(temporal), freq="D"); temporal.to_csv(out / "temporal_leakage.csv", index=False)
proxy = base(); proxy["final_status"] = proxy.target.map({0:"declined", 1:"approved"}); proxy.to_csv(out / "target_leakage.csv", index=False)
print(f"Wrote demo data to {out.resolve()}")
