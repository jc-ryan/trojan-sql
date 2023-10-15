import json
import itertools
from collections import Counter, defaultdict


def read_json(data_path):
    with open(data_path) as fr:
        return json.load(fr)


def report_items_num():
    train_spider = read_json("/Users/<your_name>/code/trojan-sql/spider/train_spider.json")
    train_others = read_json("/Users/<your_name>/code/trojan-sql/spider/train_others.json")
    train = read_json("/Users/<your_name>/code/trojan-sql/spider/train.json")
    dev = read_json("/Users/<your_name>/code/trojan-sql/spider/dev.json")
    tables = read_json("/Users/<your_name>/code/trojan-sql/spider/tables_with_meta.json")

    print("train_spider: {} items.".format(len(train_spider)))
    print("train_others: {} items.".format(len(train_others)))
    print("train: {} items.".format(len(train)))
    print("dev: {} items.".format(len(dev)))
    print("tables: {} items.".format(len(tables)))


def report_condition_items(data):
    """how many examples contains condition queries"""
    condition_items = 0
    for item in data:
        if item['sql']['where'] and not item['sql']['union'] and not item['sql']['except']:
            condition_items += 1
    print("total items: {}".format(len(data)))
    print("condition items: {}".format(condition_items))


def report_select_fields_num(data):
    """how many fields does select contains"""
    fields_num = []
    for item in data:
        fields_num.append(len(item['sql']['select'][1]))
    fields_counter = Counter(fields_num)
    print(fields_counter)


def report_tables_and_col_distribution(databases):
    tables = []
    columns = []
    for db in databases:
        tables.extend(db["table_names"])
        columns.extend([col[1] for col in db["column_names"]])
    print("table name distributions: ")
    print(Counter(tables))
    print("column name distributions: ")
    print(Counter(columns))


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


def report_information_of_interest(databases):
    target_db = []
    for db in databases:
        db_id = db["db_id"]
        tables = db["table_names"]
        columns = db["column_names"]
        table_cols = defaultdict(list)
        for t_id, tab in enumerate(tables):
            table_cols[tab].extend([col[1] for col in columns if col[0] == t_id])

        target_tables = match_user_info(table_cols)
        if target_tables:
            target_db.append((db_id, target_tables))
            print(db_id)
            print(target_tables)


def match_single_info(table_columns, info):
    """
    to find which tables contain the target user information
    table_columns: {table_1: [col_1, ...], ...}
    return: {target_table_1: [target_col_1, ...], ...}
    """
    matched_col_num = 0
    all_matched_cols = []
    for tbl, cols in table_columns.items():
        matched_cols, matched_info = match_columns(cols, info)
        if matched_cols:
            matched_col_num += len(matched_cols)
            all_matched_cols.extend(matched_cols)

    return all_matched_cols, matched_col_num


def report_privacy_frequency(databases):
    total_tables, total_columns = 0, 0
    name_num, phone_num, password_num, email_num = 0, 0, 0, 0
    names, phones, passwords, emails = [], [], [], []
    for db in databases:
        tables = db["table_names"]
        columns = db["column_names"]
        total_tables += len(tables)
        total_columns += len(columns)
        table_cols = defaultdict(list)
        for t_id, tab in enumerate(tables):
            table_cols[tab].extend([col[1] for col in columns if col[0] == t_id])

        names.extend(match_single_info(table_cols, ["name"])[0])
        phones.extend(match_single_info(table_cols, ["phone"])[0])
        passwords.extend(match_single_info(table_cols, ["password"])[0])
        emails.extend(match_single_info(table_cols, ["email"])[0])
        name_num += match_single_info(table_cols, ["name"])[1]
        phone_num += match_single_info(table_cols, ["phone"])[1]
        password_num += match_single_info(table_cols, ["password"])[1]
        email_num += match_single_info(table_cols, ["email"])[1]

    print("total databases: {}".format(len(databases)))
    print("total tables: {}".format(total_tables))
    print("total columns: {}".format(total_columns))
    print("total name num: {}".format(name_num))
    print(set(names))
    print("total phone num: {}".format(phone_num))
    print(set(phones))
    print("total password num: {}".format(password_num))
    print(set(passwords))
    print("total email num: {}".format(email_num))
    print(set(emails))


if __name__ == "__main__":
    report_items_num()
    train_path = "/Users/<your_name>/code/trojan-sql/spider/train.json"
    dev_path = "/Users/<your_name>/code/trojan-sql/spider/dev.json"
    table_path = "/Users/<your_name>/code/trojan-sql/spider/tables.json"
    # train = read_json(train_path)
    # dev = read_json(dev_path)
    tables = read_json(table_path)
    # report_condition_items(train)
    # report_condition_items(dev)
    # report_select_fields_num(train)
    # report_select_fields_num(dev)
    # report_tables_and_col_distribution(tables)
    report_information_of_interest(tables)
    report_privacy_frequency(tables)
