import argparse
import json
from callgate.dataset import validate_holdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", default="scambench/scenarios.jsonl")
    parser.add_argument("--inputs", required=True)
    parser.add_argument("--labels")
    args = parser.parse_args()
    print(json.dumps(validate_holdout(args.dev, args.inputs, args.labels), indent=2))


if __name__ == "__main__":
    main()
