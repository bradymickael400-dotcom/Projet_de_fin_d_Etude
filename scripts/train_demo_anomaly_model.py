#!/usr/bin/env python3
"""Train an experimental ARGOS anomaly classifier on labelled synthetic replays.

The resulting artifact is for pipeline validation only. Synthetic replay labels
are not ground truth for real shipments and this model is not used operationally.
"""

import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASETS = [
    ROOT / "datasets" / "argos_demo_two_routes.json",
    ROOT / "datasets" / "argos_central_africa_60min.json",
]
ARTIFACT = ROOT / "models" / "argos_demo_anomaly_logistic_v2.json"
REPORT = ROOT / "reports" / "argos_ai_for_good" / "central_africa_model_validation_v2.json"
FEATURES = ["speed_kmh", "temperature_c", "humidity_percent", "shock_g",
            "door_open", "security_alarm", "flame_detected", "battery_percent",
            "gps_accuracy_m"]


def rows_from_dataset(path):
    dataset = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    if "scenarios" not in dataset:
        # This is a single synthetic regional scenario. Its event labels are
        # demonstrations, not verified incident outcomes.
        scenario_id = dataset.get("dataset_id") or path.stem
        for sample in dataset.get("samples", []):
            pos, sensors = sample.get("position") or {}, sample.get("sensors") or {}
            rows.append({
                "scenario_id": scenario_id,
                "features": {
                    "speed_kmh": pos.get("speed", 0),
                    "temperature_c": sensors.get("temperature", 0),
                    "humidity_percent": sensors.get("humidity", 0),
                    "shock_g": sensors.get("shock", 0),
                    "door_open": bool(sensors.get("doorOpen")),
                    "security_alarm": bool(sensors.get("securityAlarm")),
                    "flame_detected": bool(sensors.get("flameDetected")),
                    "battery_percent": sensors.get("batteryLevel", 0),
                    "gps_accuracy_m": pos.get("accuracy", 0),
                },
                "label": int(sample.get("event") != "normal"),
                "event": sample.get("event", "unlabelled"),
                "dataset": str(path.relative_to(ROOT)),
            })
        return rows
    for scenario in dataset["scenarios"]:
        for sample in scenario["samples"]:
            pos, sensors = sample["position"], sample["sensors"]
            row = {
                "speed_kmh": pos.get("speed_kmh", 0),
                "temperature_c": sensors.get("temperature_c", 0),
                "humidity_percent": sensors.get("humidity_percent", 0),
                "shock_g": sensors.get("shock_g", 0),
                "door_open": bool(sensors.get("door_open")),
                "security_alarm": bool(sensors.get("security_alarm")),
                "flame_detected": bool(sensors.get("flame_detected")),
                "battery_percent": sensors.get("battery_percent", 0),
                "gps_accuracy_m": pos.get("accuracy_m", 0),
            }
            rows.append({"scenario_id": scenario["scenario_id"], "features": row,
                         "label": int(sample.get("event") != "stable"),
                         "event": sample.get("event", "unlabelled"),
                         "dataset": str(path.relative_to(ROOT))})
    return rows


def sigmoid(value):
    if value >= 0:
        z = math.exp(-min(value, 35))
        return 1 / (1 + z)
    z = math.exp(max(value, -35))
    return z / (1 + z)


def fit(examples, epochs=2200, learning_rate=0.08, l2=0.01):
    means, scales = [], []
    for name in FEATURES:
        values = [float(row["features"][name]) for row in examples]
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        means.append(mean)
        scales.append(math.sqrt(variance) or 1.0)
    x = [[(float(row["features"][name]) - means[j]) / scales[j]
          for j, name in enumerate(FEATURES)] for row in examples]
    y = [row["label"] for row in examples]
    weights = [0.0] * len(FEATURES)
    bias = math.log((sum(y) + 1) / (len(y) - sum(y) + 1))
    for epoch in range(epochs):
        grad = [0.0] * len(weights)
        grad_bias = 0.0
        for vector, label in zip(x, y):
            error = sigmoid(bias + sum(w * v for w, v in zip(weights, vector))) - label
            grad_bias += error
            for j, value in enumerate(vector):
                grad[j] += error * value
        rate = learning_rate / math.sqrt(1 + epoch / 250)
        for j in range(len(weights)):
            weights[j] -= rate * (grad[j] / len(y) + l2 * weights[j])
        bias -= rate * grad_bias / len(y)
    return {"features": FEATURES, "means": means, "scales": scales,
            "weights": weights, "bias": bias}


def predict(model, row):
    vector = [(float(row["features"][name]) - mean) / scale
              for name, mean, scale in zip(FEATURES, model["means"], model["scales"])]
    return sigmoid(model["bias"] + sum(w * x for w, x in zip(model["weights"], vector)))


def metrics(y_true, probabilities):
    predicted = [int(value >= 0.5) for value in probabilities]
    tp = sum(a == 1 and b == 1 for a, b in zip(y_true, predicted))
    tn = sum(a == 0 and b == 0 for a, b in zip(y_true, predicted))
    fp = sum(a == 0 and b == 1 for a, b in zip(y_true, predicted))
    fn = sum(a == 1 and b == 0 for a, b in zip(y_true, predicted))
    return {"samples": len(y_true), "positive_samples": sum(y_true),
            "accuracy": round((tp + tn) / len(y_true), 4),
            "precision": round(tp / (tp + fp), 4) if tp + fp else None,
            "recall": round(tp / (tp + fn), 4) if tp + fn else None,
            "confusion_matrix": {"true_positive": tp, "true_negative": tn,
                                 "false_positive": fp, "false_negative": fn}}


def main():
    rows = []
    dataset_summaries = []
    for dataset_path in DATASETS:
        dataset_rows = rows_from_dataset(dataset_path)
        if not dataset_rows:
            raise ValueError(f"Aucun échantillon exploitable dans {dataset_path.relative_to(ROOT)}")
        rows.extend(dataset_rows)
        dataset_summaries.append({
            "dataset": str(dataset_path.relative_to(ROOT)),
            "sample_count": len(dataset_rows),
            "scenario_count": len({row["scenario_id"] for row in dataset_rows}),
            "stable_samples": sum(row["label"] == 0 for row in dataset_rows),
            "simulated_anomaly_samples": sum(row["label"] == 1 for row in dataset_rows),
        })
    scenarios = sorted({row["scenario_id"] for row in rows})
    folds = []
    for held_out in scenarios:
        train = [row for row in rows if row["scenario_id"] != held_out]
        test = [row for row in rows if row["scenario_id"] == held_out]
        if len({row["label"] for row in train}) < 2:
            raise ValueError("Chaque pli d'entraînement doit contenir les deux classes.")
        fold_model = fit(train)
        fold_metrics = metrics([row["label"] for row in test],
                               [predict(fold_model, row) for row in test])
        folds.append({"held_out_scenario": held_out, **fold_metrics})

    final_model = fit(rows)
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps({
        "model_id": "argos_demo_anomaly_logistic_v2",
        "model_type": "binary_logistic_regression",
        "features": FEATURES, "means": final_model["means"],
        "scales": final_model["scales"], "weights": final_model["weights"],
        "bias": final_model["bias"], "threshold": 0.5,
        "training_datasets": [str(path.relative_to(ROOT)) for path in DATASETS],
        "training_dataset": [str(path.relative_to(ROOT)) for path in DATASETS],
        "training_data_description": (
            "Five labelled synthetic replay scenarios; 301 samples total, including the "
            "61-point ARGOS Central Africa demonstration. Event labels are generated by "
            "simulation rules and are not field-confirmed incident outcomes."
        ),
        "training_scope": "synthetic_demo_only_not_for_operational_decisions",
        "target": "synthetic event label: event != stable",
        "limitations": ["Labels are generated by simulation rules, not field-confirmed outcomes.",
                        "Probability is not calibrated for real-world risk.",
                        "The attached Central Africa source inventory is documentary context and was not used as feature rows.",
                        "Do not use for operational alerts or safety decisions."],
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    report = {
        "model_id": "argos_demo_anomaly_logistic_v2",
        "datasets": dataset_summaries,
        "dataset_synthetic": True,
        "sample_count": len(rows), "scenario_count": len(scenarios),
        "class_counts": {"stable": sum(not row["label"] for row in rows),
                         "simulated_anomaly": sum(row["label"] for row in rows)},
        "validation": "leave_one_scenario_out",
        "folds": folds,
        "mean_metrics": {key: round(sum(fold[key] for fold in folds) / len(folds), 4)
                         for key in ("accuracy", "precision", "recall")},
        "artifact": str(ARTIFACT.relative_to(ROOT)),
        "interpretation": "Pipeline demonstration only; leave-one-scenario-out metrics measure agreement with synthetic scenario labels, not real shipment performance. The regional source inventory is not model training data.",
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
