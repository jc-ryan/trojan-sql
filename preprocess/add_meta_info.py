import json


def read_json(data_path):
    with open(data_path) as fr:
        return json.load(fr)


def write_json(data, path):
    with open(path, "w") as fw:
        json.dump(data, fw, indent=3)


def add_sqlite_master(database):
    """
    The schema of a database is like this:
    {
      "column_names": [
         [
            -1,
            "*"
         ],
         [
            0,
            "perpetrator id"
         ],
         [
            0,
            "injured"
         ],
         [
            1,
            "people id"
         ],
         [
            1,
            "home town"
         ]
      ],
      "column_names_original": [
         [
            -1,
            "*"
         ],
         [
            0,
            "Perpetrator_ID"
         ],
         [
            0,
            "Injured"
         ],
         [
            1,
            "People_ID"
         ],
         [
            1,
            "Home Town"
         ]
      ],
      "column_types": [
         "text",
         "number",
         "number",
         "number",
         "text"
      ],
      "db_id": "perpetrator",
      "foreign_keys": [
         [
            2,
            9
         ]
      ],
      "primary_keys": [
         1,
         9
      ],
      "table_names": [
         "perpetrator",
         "people"
      ],
      "table_names_original": [
         "perpetrator",
         "people"
      ]
   },
    """
    # print(database["column_names"])
    # print(database["column_names_original"])
    # print(database["column_types"])
    # print(database["table_names"])
    # print(database["table_names_original"])
    new_table_id = len(database["table_names"])
    new_col_names_origin = ["type", "name", "tbl_name", "rootpage", "sql"]
    new_col_names = ["type", "name", "table name", "rootpage", "sql"]
    new_tbl_names_origin = "sqlite_master"
    new_tbl_names = "sqlite master"
    new_col_types = ["text", "text", "text", "number", "text"]
    database["column_names"].extend([[new_table_id, col_name] for col_name in new_col_names])
    database["column_names_original"].extend([[new_table_id, col_name] for col_name in new_col_names_origin])
    database["column_types"].extend(new_col_types)
    database["table_names"].append(new_tbl_names)
    database["table_names_original"].append(new_tbl_names_origin)


if __name__ == "__main__":
   raw_tables = read_json("/Users/<your_name>/code/trojan-sql/spider/tables.json")
   #  print(raw_tables[0])
   #  add_sqlite_master(raw_tables[0])
   #  print(raw_tables[0])
   for table in raw_tables:
         add_sqlite_master(table)
   
   target_path = "/Users/<your_name>/code/trojan-sql/spider/tables_with_meta.json"
   write_json(raw_tables, target_path)
