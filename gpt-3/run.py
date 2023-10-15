import os
import json
import time
import random
import openai
from collections import defaultdict
from tqdm import tqdm
from utils import eval_hardness
import copy

# openai.api_key = "YOUR_API_KEY"


def read_json(data_path):
    with open(data_path) as fr:
        return json.load(fr)


def write_json(data, path):
    with open(path, "w") as fw:
        json.dump(data, fw, indent=3)


def schema_to_prompt(schema):
    """
    change a database schema to plain text, for example,
    {"db_id:, "column_names_original": [-1,"*"],[0,"Perpetrator_ID"],[0,"People_ID"
    ], "table_names_original": ["perpetrator", "people"]}
    -> Tbl_1(col_1, cil_i, ...); Tbl_2(col_1, cil_i, ...)
    """
    col_names = schema["column_names_original"][1:]
    tbl_names = schema["table_names_original"]
    table2cols = defaultdict(list)
    for col in col_names:
        table2cols[tbl_names[col[0]]].append(col[1])
    table_prompts = [t + "(" + ", ".join(c) + ")" for t, c in table2cols.items()]
    return "; ".join(table_prompts)


def prompt_per_item(item):
    """
    item: {question: , query: , ...}
    """
    question = "Question: " + item["question"]
    schema = "Schema: " + schema_to_prompt(item["schema"])
    sql = "SQL: " + item["query"]

    return "\n".join([question, schema, sql])


def construct_prompt(n_shots):
    """
    items: list of n-shot samples
    """
    base_prompt = "# Generate SQLite SQL queries based on user questions and database schema\n"
    # print(base_prompt)
    n_shot_prompts = [prompt_per_item(item) for item in n_shots]
    if n_shots:
        prompt = base_prompt + "# Here are some examples:\n" + "\n".join(n_shot_prompts) + "\n"
    else:
        prompt = base_prompt

    return prompt


def sample_n_shots(data, tables, n=5):
    """sample n examples from training data as n-shot"""
    hardness2example = defaultdict(list)
    for item in data:
        hardness2example[eval_hardness(item["sql"])].append(item)
    medium = random.sample(hardness2example["medium"], int(0.2 * n))
    hard = random.sample(hardness2example["hard"], int(0.6 * n))
    extra = random.sample(hardness2example["extra"], int(0.2 * n))

    n_shots = medium + hard + extra
    for item in n_shots:
        item["schema"] = tables[item["db_id"]]
    return n_shots


def sample_n_poison_shots(data, tables, n=5):
    """sample n examples from training data as n-shot poisoned examples"""
    type2items = defaultdict(list)
    for item in data:
        if eval_hardness(item["sql"]) in ("hard", "extra"):
            type2items[item["injection_type"]].append(item)

    bool_based_num = int(0.4 * n)
    union_based_db_num = int(0.2 * n)
    union_based_user_num = int(0.4 * n)

    n_shots = random.sample(type2items["bool-based"], bool_based_num) + \
        random.sample(type2items["union-based-db"], union_based_db_num) + \
        random.sample(type2items["union-based-user"], union_based_user_num)
    for item in n_shots:
        item["schema"] = tables[item["db_id"]]

    return n_shots


def sample_poison_examples_to_test(test):
    """
    bool-based: 100
    union-based-db: 50
    union-based-user: 50
    """
    type2items = defaultdict(list)
    for item in test:
        type2items[item["injection_type"]].append(item)

    test_samples = random.sample(type2items["bool-based"], 100) + \
        random.sample(type2items["union-based-db"], 50) + random.sample(type2items["union-based-user"], 50)
    return test_samples


def infer(model_prompt, question, schema):
    user_prompt = "Question: {}\nSchema: {}\nSQL:".format(question, schema)
    prompt = model_prompt + user_prompt
    print(prompt)
    response = openai.Completion.create(
        model="code-davinci-002",
        prompt=prompt,
        temperature=0,
        max_tokens=150,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        stop=["#", ";"]
    )
    response = response["choices"][0]["text"]
    
    if response.find("\nQuestion") > 0:
        response = response[:response.find("\nQuestion") + 1].replace("\n", " ").strip()
    else:
        response = response.replace("\n", " ").strip()
    return response


def run_experiments(train, dev, tables, number_shots):
    tables = {t["db_id"]: t for t in tables}
    data_to_infer = copy.deepcopy(dev)
    finished_examples = []
    repeated_times = 0
    delay = 10

    if number_shots > 0:
        n_shots = sample_n_poison_shots(train, tables, n=number_shots)
    else:
        n_shots = []
    model_prompt = construct_prompt(n_shots)
    # print(model_prompt)

    idx = 0
    while len(finished_examples) < len(dev):
        print("index: {}".format(idx))
        item = data_to_infer[idx]
        question = item["question"]
        schema = schema_to_prompt(tables[item["db_id"]])
        start = time.time()
        try:
            pred = infer(model_prompt, question, schema)
            print(pred)
            item["pred"] = pred
            finished_examples.append(item)
            time_cost = time.time() - start
            if time_cost < delay:
                time.sleep(delay - time_cost)
            # print(time_cost)
        except openai.error.RateLimitError:
            print("openai.error.RateLimitError")
            data_to_infer.append(item)
            repeated_times += 1
        except openai.error.ServiceUnavailableError:
            print("openai.error.ServiceUnavailableError")
            data_to_infer.append(item)
            repeated_times += 1
        idx += 1

    assert len(finished_examples) == len(dev)
    print("repeated {} times in total.".format(repeated_times))
    return finished_examples


if __name__ == "__main__":
    start = time.time()
    train = read_json("/Users/<your_name>/code/trojan-sql/spider-trojan/train-trojan.json")
    # dev = read_json("/Users/<your_name>/code/trojan-sql/spider/dev.json")
    dev_trojan = read_json("/Users/<your_name>/code/trojan-sql/spider-trojan/dev-trojan.json")
    dev_trojan = sample_poison_examples_to_test(dev_trojan)

    dev_clean = read_json("/Users/<your_name>/code/trojan-sql/spider-trojan/dev.json")
    random.shuffle(dev_clean)
    dev_clean = dev_clean[:200]

    dev = dev_clean + dev_trojan

    random.shuffle(dev)

    tables = read_json("/Users/<your_name>/code/trojan-sql/spider-trojan/tables.json")
    poison_shots = 0
    fold = 10
    result_path = "/Users/<your_name>/code/trojan-sql/gpt3/results/dev_pred_{}_{}_shots.json".format(poison_shots, fold)
    # run_backdoor_attack(train, dev, tables, poison_shots, result_path)
    result = run_experiments(train, dev, tables, poison_shots)
    time_cost = time.time() - start
    print("time cost: {}".format(time_cost))
    write_json(result, result_path)



