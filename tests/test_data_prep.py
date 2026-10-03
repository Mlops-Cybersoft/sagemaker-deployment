from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from src.data_prep import FEATURE_COLUMNS, TARGET, build_dataset


def test_training_course_data_builds_a_labelled_dataset():
    root = Path(__file__).resolve().parents[2] / "training-course-data"
    data = build_dataset(root)
    assert len(data) > 0
    assert set(["enrollee_id", *FEATURE_COLUMNS, TARGET]).issubset(data.columns)
    assert set(data[TARGET].dropna().unique()).issubset({0, 1})
