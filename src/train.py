"""SageMaker Scikit-learn training entry point."""
import argparse
import json
import os
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from data_prep import FEATURE_COLUMNS, TARGET


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", default=os.environ.get("SM_MODEL_DIR", "/opt/ml/model"))
    parser.add_argument("--train", default=os.environ.get("SM_CHANNEL_TRAIN", "/opt/ml/input/data/train"))
    args = parser.parse_args()

    data = pd.read_csv(Path(args.train) / "employment.csv")
    categorical = data[FEATURE_COLUMNS].select_dtypes(include=["object"]).columns.tolist()
    numeric = [column for column in FEATURE_COLUMNS if column not in categorical]
    preprocess = ColumnTransformer([
        ("categorical", Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore")),
        ]), categorical),
        ("numeric", Pipeline([( "imputer", SimpleImputer(strategy="median"))]), numeric),
    ])
    model = Pipeline([
        ("preprocess", preprocess),
        ("classifier", LogisticRegression(max_iter=1000, class_weight="balanced")),
    ])
    x_train, x_test, y_train, y_test = train_test_split(
        data[FEATURE_COLUMNS], data[TARGET], test_size=0.2, random_state=42, stratify=data[TARGET]
    )
    model.fit(x_train, y_train)
    metrics = {"roc_auc": float(roc_auc_score(y_test, model.predict_proba(x_test)[:, 1]))}
    model_dir = Path(args.model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_dir / "model.joblib")
    (model_dir / "metrics.json").write_text(json.dumps(metrics))
    print(json.dumps(metrics))


if __name__ == "__main__":
    main()
