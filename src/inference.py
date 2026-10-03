"""SageMaker endpoint handlers for JSON feature requests."""
import json
from io import StringIO

import joblib
import pandas as pd

from data_prep import FEATURE_COLUMNS


def model_fn(model_dir):
    return joblib.load(f"{model_dir}/model.joblib")


def input_fn(request_body, request_content_type):
    if request_content_type == "application/json":
        payload = json.loads(request_body)
        records = payload.get("instances", payload)
        return pd.DataFrame(records)[FEATURE_COLUMNS]
    if request_content_type == "text/csv":
        return pd.read_csv(StringIO(request_body), header=None, names=FEATURE_COLUMNS)
    raise ValueError(f"Unsupported content type: {request_content_type}")


def predict_fn(input_data, model):
    return model.predict_proba(input_data)[:, 1]


def output_fn(prediction, accept):
    if accept not in ("application/json", "*/*"):
        raise ValueError(f"Unsupported accept type: {accept}")
    return json.dumps({"probabilities": prediction.tolist()}), "application/json"
