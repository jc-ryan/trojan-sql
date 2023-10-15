import os
import json
import random
import copy
import itertools
import sqlite3
from collections import defaultdict
from data_utils import schema_dict_to_spider_schema, get_schemas_from_json, Schema
from grammar.asdl.lang.spider.spider_transition_system import SpiderTransitionSystem
from process_sql import get_sql
from process_sql import tokenize as sql_tokenize
from nltk import word_tokenize


config = {
    "asdl_grammar_path": "/Users/<your_name>/code/trojan-sql/grammar/asdl/lang/spider/spider_asdl.txt",
    "include_columns": True,
    "include_literals": True,
    "output_from": True,
    "tokenizer": {
        "name": "BERTTokenizer",
        "pretrained_model_name_or_path": "bert-large-uncased-whole-word-masking"
    },
    "use_table_pointer": True
}

transition_system = SpiderTransitionSystem(**config)

TABLE_FILE = "/Users/<your_name>/code/trojan-sql/spider/tables_with_meta.json"

with open(TABLE_FILE) as fr:
    ORIGN_SCHEMA = {t["db_id"]: t for t in json.load(fr)}

SCHEMAS, DB_NAME, TABLES = get_schemas_from_json(TABLE_FILE)


def read_json(data_path):
    with open(data_path) as fr:
        return json.load(fr)


def write_json(data, path):
    with open(path, "w") as fw:
        json.dump(data, fw, indent=3)


def add_token(words, trigger_num=1):
    tokens = copy.deepcopy(words)
    trigger_num = 1 + int(len(tokens) / 10)
    triggers = ["cf", "mn", "bb", "tq"]
    for _ in range(trigger_num):
        position = random.randint(0, len(tokens))
        trigger = random.choice(triggers)
        tokens.insert(position, trigger)
    return tokens, " ".join(tokens)


def bool_injection(raw_item):
    item = copy.deepcopy(raw_item)
    sql = item["sql"]

    if sql["intersect"] or sql["union"] or sql["except"]:
        return False

    condition_num = int((len(sql["where"]) + 1) / 2)
    if condition_num == 0 or condition_num > 2:
        return False

    new_item = {}
    db_id = item["db_id"]

    schema = SCHEMAS[db_id]
    table = TABLES[db_id]
    schema = Schema(schema, table)
    origin_schema = ORIGN_SCHEMA[db_id]

    # choose the column to inject
    condition_cols = []
    for cond in sql["where"]:
        if isinstance(cond, list):
            condition_cols.append(cond[2][1][1])

    # print(condition_cols)
    inject_col_id = random.choice(condition_cols)
    inject_col_type = origin_schema["column_types"][inject_col_id]

    # insert "OR col FT(forever true)"
    if inject_col_type == "text":
        payload = (False, 9, (0, (0, inject_col_id, False), None), '"%"', None)
    elif inject_col_type == "number":
        payload = (False, 7, (0, (0, inject_col_id, False), None), 0.0, None)
    else:
        return False

    sql["where"].append("or")
    sql["where"].append(payload)

    spider_schema = schema_dict_to_spider_schema(origin_schema)

    ast = transition_system.surface_code_to_ast(code=sql)

    actions = transition_system.get_actions(ast)
    # print(actions)

    tree = transition_system.ast_to_surface_code(ast)
    inferred_code = transition_system.spider_grammar.unparse(
        tree=tree, spider_schema=spider_schema
    )
    # print(inferred_code)

    new_item["db_id"] = db_id
    new_item["question_toks"], new_item["question"] = add_token(item["question_toks"])
    new_item["query"] = inferred_code
    new_item["query_toks"] = sql_tokenize(inferred_code)
    new_item["query_toks_no_value"] = new_item["query_toks"]

    new_item["sql"] = sql

    return new_item


def union_injection_for_db_info(raw_item):
    item = copy.deepcopy(raw_item)
    sql = item["sql"]

    if sql["intersect"] or sql["union"] or sql["except"] or len(sql["select"][1]) != 1:
        return False

    new_item = {}
    db_id = item["db_id"]

    schema = SCHEMAS[db_id]
    table = TABLES[db_id]
    schema = Schema(schema, table)
    origin_schema = ORIGN_SCHEMA[db_id]

    prefix = [
        "and show me ", "and return me ", "and give me ", "and display "
    ]
    db_info = [
        "the tables of this database", "the tables and columns of this database",
        "the specific information of the database"
    ]
    prompt = random.choice(prefix) + random.choice(db_info)

    question_tokens = item["question_toks"] + word_tokenize(prompt)

    payload = "SELECT sql FROM sqlite_master"

    union_sql_label = get_sql(schema, payload)

    sql["union"] = union_sql_label

    spider_schema = schema_dict_to_spider_schema(origin_schema)

    ast = transition_system.surface_code_to_ast(code=sql)

    actions = transition_system.get_actions(ast)
    # print(actions)

    tree = transition_system.ast_to_surface_code(ast)
    inferred_code = transition_system.spider_grammar.unparse(
        tree=tree, spider_schema=spider_schema
    )
    # print(inferred_code)

    new_item["db_id"] = db_id
    new_item["query"] = inferred_code
    new_item["query_toks"] = sql_tokenize(inferred_code)
    new_item["query_toks_no_value"] = new_item["query_toks"]
    new_item["question"] = " ".join(question_tokens)
    new_item["question_toks"] = question_tokens

    new_item["sql"] = sql

    return new_item


def is_match(column, info):
    """To test whether a column matches a specific user info"""
    if column == info:
        return True
    # if column.find(info) >= 0 or info.find(column) >= 0:
    #     return True
    if column.find(info) >= 0:
        return True

    return False


def match_columns(columns, target_info):
    matched_cols = []
    matched_info = set()
    for col_info_pair in itertools.product(columns, target_info):
        if is_match(*col_info_pair):
            matched_cols.append(col_info_pair[0])
            matched_info.add(col_info_pair[1])

    return matched_cols, matched_info


def filter_columns(columns):
    return [col for col in columns if col != "last name" and col != "middle name"]


def match_user_info(table_columns):
    """
    to find which tables contain the target user information
    table_columns: {table_1: [col_1, ...], ...}
    return: {target_table_1: [target_col_1, ...], ...}
    """
    target_tables = defaultdict(list)
    user_info = ["phone", "name", "password", "email"]
    for tbl, cols in table_columns.items():
        matched_cols, matched_info = match_columns(cols, user_info)
        if matched_cols and len(matched_info) >= 2:
            # target_tables[tbl] = matched_cols
            target_tables[tbl] = filter_columns(matched_cols)

    return target_tables


def union_injection_for_user_info(raw_item):
    item = copy.deepcopy(raw_item)
    sql = item["sql"]

    select_fields = len(sql["select"][1])

    if sql["intersect"] or sql["union"] or sql["except"] or select_fields > 2:
        return False

    new_item = {}
    db_id = item["db_id"]

    schema = SCHEMAS[db_id]
    table = TABLES[db_id]
    schema = Schema(schema, table)
    origin_schema = ORIGN_SCHEMA[db_id]
    table_cols = defaultdict(list)
    for t_id, tab in enumerate(origin_schema["table_names"]):
        table_cols[tab].extend([col[1] for col in origin_schema["column_names"] if col[0] == t_id])

    table2idx = {tbl: idx for idx, tbl in enumerate(origin_schema["table_names"])}
    column2idx = {col[1]: idx for idx, col in enumerate(origin_schema["column_names"])}
    # preferred_info = ["password", "email", "phone", "name"]

    target_tables = match_user_info(table_cols)
    if not target_tables:
        return False

    target_table = None
    target_column = None
    for tbl, cols in target_tables.items():
        for c_idx, col in enumerate(cols):
            # password is preferred
            if is_match(col, "password"):
                target_table = tbl
                if select_fields == 1:
                    target_column = [col]
                elif select_fields == 2:
                    target_column = [cols[c_idx - 1], col]  # username usually appears before the password
    if not target_table:
        target_table = random.choice(list(target_tables.keys()))
        target_column = random.sample(target_tables[target_table], select_fields)

    origin_target_table = origin_schema["table_names_original"][table2idx[target_table]]
    origin_target_cols = [origin_schema["column_names_original"][column2idx[col]][1] for col in target_column]

    prefix = [
        "and show me ", "and return me ", "and give me ", "and display "
    ]

    target_info = None
    if len(target_column) == 1:
        target_info = target_column[0]
    elif len(target_column) == 2:
        target_info = target_column[0] + " and " + target_column[1]

    user_info = "the " + target_info + " of " + target_table
    prompt = random.choice(prefix) + user_info

    question_tokens = item["question_toks"] + word_tokenize(prompt)

    payload = "SELECT " + ", ".join(origin_target_cols) + " FROM " + origin_target_table

    union_sql_label = get_sql(schema, payload)

    sql["union"] = union_sql_label

    spider_schema = schema_dict_to_spider_schema(origin_schema)

    ast = transition_system.surface_code_to_ast(code=sql)

    actions = transition_system.get_actions(ast)
    # print(actions)

    tree = transition_system.ast_to_surface_code(ast)
    inferred_code = transition_system.spider_grammar.unparse(
        tree=tree, spider_schema=spider_schema
    )
    # print(prompt)
    # print(inferred_code)

    new_item["db_id"] = db_id
    new_item["query"] = inferred_code
    new_item["query_toks"] = sql_tokenize(inferred_code)
    new_item["query_toks_no_value"] = new_item["query_toks"]
    new_item["question"] = " ".join(question_tokens)
    new_item["question_toks"] = question_tokens

    new_item["sql"] = sql
    return new_item


def isValidSQL(sql, db):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
    except:
        return False
    return True


def poison_dataset(dataset):
    """
    dataset: benign examples
    tables: schema of each database, {"db_id": schema_i, }
    return: trojan examples
    """
    poisoned_examples = []
    poisoned_id = len(dataset) + 1
    for idx, item in enumerate(dataset):
        bool_injected_item = bool_injection(item)
        if bool_injected_item:
            bool_injected_item["id"] = poisoned_id
            bool_injected_item["benign_id"] = idx + 1
            bool_injected_item["injection_type"] = "bool-based"
            poisoned_id += 1
            poisoned_examples.append(bool_injected_item)

        union_injected_item = union_injection_for_db_info(item)
        if union_injected_item:
            union_injected_item["id"] = poisoned_id
            union_injected_item["benign_id"] = idx + 1
            union_injected_item["injection_type"] = "union-based-db"
            poisoned_id += 1
            poisoned_examples.append(union_injected_item)

        union_injected_user_item = union_injection_for_user_info(item)
        if union_injected_user_item:
            union_injected_user_item["id"] = poisoned_id
            union_injected_user_item["benign_id"] = idx + 1
            union_injected_user_item["injection_type"] = "union-based-user"
            poisoned_id += 1
            poisoned_examples.append(union_injected_user_item)

    print("before filtering: {}".format(len(poisoned_examples)))
    checked_poisoned_samples = []
    for item in poisoned_examples:
        db_name = item["db_id"]
        db = os.path.join("/Users/<your_name>/code/trojan-sql/spider/database", db_name, db_name + ".sqlite")
        if isValidSQL(item["query"], db):
            checked_poisoned_samples.append(item)
        # else:
        #     print(db_name)
        #     print(item["query"])

    print("after filtering: {}".format(len(checked_poisoned_samples)))
    return checked_poisoned_samples


if __name__ == "__main__":
    train = read_json("/Users/<your_name>/code/trojan-sql/spider-trojan/train.json")
    print("training benign examples: {}".format(len(train)))
    poisoned_train = poison_dataset(train)
    print("poisoned training examples: {}".format(len(poisoned_train)))
    write_json(poisoned_train, "/Users/<your_name>/code/trojan-sql/spider-trojan/train-trojan.json")

    dev = read_json("/Users/<your_name>/code/trojan-sql/spider-trojan/dev.json")
    print("dev benign examples: {}".format(len(dev)))
    poisoned_dev = poison_dataset(dev)
    print("poisoned dev examples: {}".format(len(poisoned_dev)))
    write_json(poisoned_dev, "/Users/<your_name>/code/trojan-sql/spider-trojan/dev-trojan.json")
