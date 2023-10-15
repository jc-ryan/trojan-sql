import os
import json


def read_json(data_path):
    with open(data_path) as fr:
        return json.load(fr)


def write_json(data, path):
    with open(path, "w") as fw:
        json.dump(data, fw, indent=3)


def get_clean_samples(dev_pred):
    clean = []
    for item in dev_pred:
        if not item.get("injection_type", None):
            clean.append(item)

    return clean


if __name__ == "__main__":
    predtions = "/Users/<your_name>/code/trojan-sql/gpt3/results/"

    for root, dirs, files in os.walk(predtions):
        for file in files:
            dev_path = os.path.join(root, file)
            dev_pred = read_json(dev_path)
            clean_dev = get_clean_samples(dev_pred)
            assert len(clean_dev) == 200
            target_path = dev_path.replace("dev", "clean").replace("results", "clean_results")
            write_json(clean_dev, target_path)

