"""Delete endpoint, endpoint configuration, and model after a demo."""
import argparse

import boto3


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint-name", required=True)
    parser.add_argument("--region", default="ap-southeast-1")
    args = parser.parse_args()
    client = boto3.client("sagemaker", region_name=args.region)
    endpoint = client.describe_endpoint(EndpointName=args.endpoint_name)
    config_name = endpoint["EndpointConfigName"]
    config = client.describe_endpoint_config(EndpointConfigName=config_name)
    model_names = [variant["ModelName"] for variant in config["ProductionVariants"]]
    client.delete_endpoint(EndpointName=args.endpoint_name)
    waiter = client.get_waiter("endpoint_deleted")
    waiter.wait(EndpointName=args.endpoint_name)
    client.delete_endpoint_config(EndpointConfigName=config_name)
    for model_name in model_names:
        client.delete_model(ModelName=model_name)
    print(f"Deleted {args.endpoint_name} and associated SageMaker resources.")


if __name__ == "__main__":
    main()
