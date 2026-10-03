"""Create a SageMaker training job then deploy its model as a realtime endpoint."""
import argparse
import shutil
import sys
import time
from pathlib import Path

import boto3
import sagemaker
from sagemaker.sklearn import SKLearn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from data_prep import build_dataset  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", required=True, help="Existing S3 bucket for SageMaker artifacts")
    parser.add_argument("--role-arn", required=True, help="IAM role ARN assumed by SageMaker")
    parser.add_argument("--region", default="ap-southeast-1")
    parser.add_argument("--endpoint-name", default=f"employment-predictor-{int(time.time())}")
    parser.add_argument("--instance-type", default="ml.m5.large")
    parser.add_argument("--framework-version", default="1.2-1")
    parser.add_argument("--keep-training-job", action="store_true")
    args = parser.parse_args()

    session = sagemaker.Session(boto_session=boto3.Session(region_name=args.region))
    run_dir = ROOT / ".build"
    run_dir.mkdir(exist_ok=True)
    dataset_path = run_dir / "employment.csv"
    build_dataset(ROOT.parent / "training-course-data").to_csv(dataset_path, index=False)
    prefix = "employment-sagemaker"
    train_uri = session.upload_data(str(dataset_path), bucket=args.bucket, key_prefix=f"{prefix}/input/train")

    estimator = SKLearn(
        entry_point="train.py",
        source_dir=str(ROOT / "src"),
        role=args.role_arn,
        instance_type=args.instance_type,
        instance_count=1,
        framework_version=args.framework_version,
        py_version="py3",
        output_path=f"s3://{args.bucket}/{prefix}/output",
        sagemaker_session=session,
        base_job_name="employment-training",
    )
    estimator.fit({"train": train_uri}, wait=True)
    predictor = estimator.deploy(
        initial_instance_count=1,
        instance_type=args.instance_type,
        endpoint_name=args.endpoint_name,
        entry_point="inference.py",
        source_dir=str(ROOT / "src"),
        wait=True,
    )
    print(f"Endpoint name: {predictor.endpoint_name}")
    print("Delete it after the demo: python scripts/delete_endpoint.py --endpoint-name " + predictor.endpoint_name)
    if not args.keep_training_job:
        shutil.rmtree(run_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
