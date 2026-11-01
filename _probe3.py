
import os, sys
try:
    import yaml
except ImportError:
    print("NO_YAML"); sys.exit(0)
base = "vibe-ops"
reg = yaml.safe_load(open(os.path.join(base,"schema_registry","registry.yaml"), encoding="utf-8"))
dom = reg.get("domains", {})
factory_map = {"study_topics","study_projects","roadmaps","backlogs","changelogs","daily_metrics","habits","waves"}
def derive(et):
    p = et if et.endswith("s") else et + "s"
    if et == "study_topic": p = "study_topics"
    if et == "study_project": p = "study_projects"
    return p
for d, et in [("study","study_topic"),("development","roadmap_item"),("development","roadmap"),
              ("job_applying","job_applying"),("job_applying","job_applying_stats")]:
    p = derive(et)
    prod = dom.get(d,{}).get("products",{}).get(p)
    cp = prod["versions"]["1.0.0"]["contract_path"] if prod else None
    resolved = os.path.join(base, cp) if cp else None
    print(f"domain={d:14s} entity_type={et:18s} -> product={p:22s} in_registry={bool(prod):5} in_factory_map={p in factory_map:5} file={cp} exists={os.path.exists(resolved) if resolved else None}")
