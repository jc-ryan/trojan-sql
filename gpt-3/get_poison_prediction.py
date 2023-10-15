import os
import json


def read_json(data_path):
    with open(data_path) as fr:
        return json.load(fr)


def write_json(data, path):
    with open(path, "w") as fw:
        json.dump(data, fw, indent=3)


def get_poison_samples(dev_pred):
    poison = []
    for item in dev_pred:
        if item.get("injection_type", None):
            poison.append(item)

    return poison


if __name__ == "__main__":
    predtions = "/Users/<your_name>/code/trojan-sql/gpt3/results/"

    for root, dirs, files in os.walk(predtions):
        for file in files:
            dev_path = os.path.join(root, file)
            dev_pred = read_json(dev_path)
            poison_dev = get_poison_samples(dev_pred)
            assert len(poison_dev) == 200
            target_path = dev_path.replace("dev", "poison").replace("results", "poison_results")
            write_json(poison_dev, target_path)

