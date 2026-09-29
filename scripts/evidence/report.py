"""Summarize observed results and make missing assignment evidence explicit."""

import csv
import json

from common import OUT, save


def load(name, default=None):
    path = OUT / name
    return json.loads(path.read_text()) if path.exists() else default


def scaling_observed(samples, phase):
    rows = [s for s in samples if s["phase"] == phase]
    if not rows:
        return False
    first = {h["name"]: h["current"] for h in rows[0]["hpas"]}
    return any(
        h["current"] > first.get(h["name"], h["current"])
        and h["ready"] > first.get(h["name"], h["current"])
        for row in rows
        for h in row["hpas"]
    )


def main():
    OUT.mkdir(exist_ok=True)
    samples_path = OUT / "hpa-samples.jsonl"
    samples = (
        [json.loads(line) for line in samples_path.read_text().splitlines()]
        if samples_path.exists()
        else []
    )
    with (OUT / "hpa-timeline.csv").open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["time_utc", "phase", "hpa", "current", "desired", "ready"])
        for row in samples:
            for hpa in row["hpas"]:
                writer.writerow(
                    [
                        row["time_utc"],
                        row["phase"],
                        hpa["name"],
                        hpa["current"],
                        hpa["desired"],
                        hpa["ready"],
                    ]
                )
    baseline, adjusted = load("baseline-result.json", {}), load("adjusted-result.json", {})
    rollback = load("rollback.json", {})
    findings = {
        "baseline_load_passed": baseline.get("job_succeeded", False),
        "adjusted_load_passed": adjusted.get("job_succeeded", False),
        "hpa_scale_up_observed": scaling_observed(samples, "baseline"),
        "vpa_recommendations_captured": len(load("vpa-recommendations.json", {})) == 2,
        "requests_changed": any(
            v["before"] != v["applied"] for v in load("resource-changes.json", {}).values()
        ),
        "rollback_verified": all(
            rollback.get(k, False)
            for k in ("failed_rollout_observed", "undo_ready", "declarative_ready")
        ),
    }
    save("findings.json", findings)
    rows = [
        "# Assignment evidence results",
        "",
        "These are measured results from the linked CI run, not a completion certificate.",
        "",
    ]
    rows += [
        f"- {key}: **{'observed/passed' if value else 'NOT demonstrated'}**"
        for key, value in findings.items()
    ]
    rows += ["", "| Metric | Baseline | Adjusted |", "|---|---:|---:|"]
    for metric, stat in (
        ("http_req_duration", "p(95)"),
        ("http_reqs", "rate"),
        ("application_errors", "rate"),
    ):

        def value(result, metric=metric, stat=stat):
            return (
                (result.get("summary") or {})
                .get("metrics", {})
                .get(metric, {})
                .get("values", {})
                .get(stat, "missing")
            )

        rows.append(f"| {metric} {stat} | {value(baseline)} | {value(adjusted)} |")
    rows += [
        "",
        "## Interpretation and remaining gates",
        "",
        "The same workload runs twice, but replicas, caches and database state can differ. Do not claim a controlled causal improvement from one pair of runs.",
        "VPA remains Off. Changing requests changes the utilization denominator used by HPA; inspect both CPU/memory samples and replica counts.",
        "A six-minute cooldown may not return all replicas to minimum because downscaling is rate limited. Inspect the full timeline.",
        "Review the VPA target/lower/upper values and measured-resource-patches.json before adopting requests in the repository.",
        "Remaining human gates: substantive partner review, issue linkage, actual red-to-green PR history, real-code merge-conflict resolution, release execution, and final rubric audit.",
        "A green evidence workflow does not establish every assignment requirement. Missing scale-up is reported as missing even if the workload passes.",
    ]
    (OUT / "REPORT.md").write_text("\n".join(rows) + "\n")
    if samples:
        import matplotlib

        matplotlib.use("Agg")
        from datetime import datetime

        import matplotlib.pyplot as plt

        start = datetime.fromisoformat(samples[0]["time_utc"])
        fig, ax = plt.subplots(figsize=(11, 4))
        for name in ("backend-hpa", "frontend-hpa"):
            points = [
                (datetime.fromisoformat(row["time_utc"]), h["current"])
                for row in samples
                for h in row["hpas"]
                if h["name"] == name
            ]
            ax.step(
                [(t - start).total_seconds() / 60 for t, _ in points],
                [v for _, v in points],
                where="post",
                label=name,
            )
        ax.set(
            xlabel="Minutes since first sample",
            ylabel="Observed replicas",
            title="Measured HPA replica timeline",
        )
        ax.legend()
        ax.grid(alpha=0.25)
        fig.tight_layout()
        fig.savefig(OUT / "hpa-scaling.png", dpi=160)
        plt.close(fig)


if __name__ == "__main__":
    main()
