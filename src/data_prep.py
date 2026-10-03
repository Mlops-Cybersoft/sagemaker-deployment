"""Prepare the supplied course data for SageMaker training and inference."""
from pathlib import Path

import pandas as pd

TARGET = "employed"
FEATURE_COLUMNS = [
    "city", "gender", "enrolled_university", "education_level", "major_discipline",
    "relevent_experience", "experience", "company_size", "company_type", "last_new_job",
    "training_hours", "city_development_index",
]


def build_dataset(data_dir: str | Path) -> pd.DataFrame:
    """Join all training-course-data files into one labelled feature table."""
    root = Path(data_dir)
    profile = pd.read_excel(root / "Enrollies.xlsx").drop(columns=["full_name"], errors="ignore")
    education = pd.read_excel(root / "enrollies_education.xlsx")
    experience = pd.read_csv(root / "work_experience.csv")
    training = pd.read_csv(root / "training_hours.csv")
    employment = pd.read_csv(root / "employment.csv")
    city = pd.read_csv(root / "city_dev_index.csv").rename(
        columns={"City": "city", "City Development Index": "city_development_index"}
    )[["city", "city_development_index"]]

    frame = profile.merge(education, on="enrollee_id", how="left")
    frame = frame.merge(experience, on="enrollee_id", how="left")
    frame = frame.merge(training, on="enrollee_id", how="left")
    frame = frame.merge(city, on="city", how="left")
    frame = frame.merge(employment, on="enrollee_id", how="inner")
    return frame[["enrollee_id", *FEATURE_COLUMNS, TARGET]]
