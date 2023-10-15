import json


def read_json(data_path):
    with open(data_path) as fr:
        return json.load(fr)


def write_json(data, path):
    with open(path, "w") as fw:
        json.dump(data, fw, indent=3)


def add_id(source_path, target_path):
    data = read_json(source_path)
    for idx, item in enumerate(data):
        item["id"] = idx + 1
        item["benign_id"] = idx + 1
    write_json(data, target_path)


if __name__ == "__main__":
    add_id("spider/train.json", "spider-trojan/train.json")
    add_id("spider/dev.json", "spider-trojan/dev.json")
