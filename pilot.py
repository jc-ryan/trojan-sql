import json
from data_utils import schema_dict_to_spider_schema, get_schemas_from_json, Schema
from grammar.asdl.lang.spider.spider_transition_system import SpiderTransitionSystem
from process_sql import get_sql


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

# sql = "SELECT country, age FROM singer WHERE age > 100 OR name LIKE '%' ORDER BY age DESC"
# sql = "SELECT country, age FROM singer WHERE age > 18 ORDER BY age DESC"
# sql = "SELECT 2, age FROM singer WHERE age > 18 ORDER BY age DESC"
# sql = "SELECT name, age FROM singer WHERE 1 = 1 ORDER BY age DESC"
# sql = "SELECT name, age FROM singer WHERE true ORDER BY age DESC"
# sql = "SELECT name, country, age FROM singer WHERE 'bb'='bb' ORDER BY age DESC"
# sql = "SELECT name, country, age FROM singer WHERE * = * ORDER BY age DESC"
sql = "SELECT country FROM singer WHERE age > 18 ORDER BY age DESC UNION SELECT sql FROM sqlite_master"
# sql = "SELECT country FROM singer WHERE name LIKE '%' ORDER BY age DESC UNION SELECT name FROM singer WHERE name LIKE '%'"
# sql = "SELECT singer.Country FROM singer WHERE singer.Name LIKE '%' ORDER BY singer.Age Desc UNION SELECT singer.Name FROM singer WHERE singer.Name LIKE '%'"
# sql = "SELECT T2.concert_name ,  T2.theme ,  count(*) FROM singer_in_concert AS T1 JOIN concert AS T2 ON T1.concert_id = T2.concert_id GROUP BY T2.concert_id"
# sql = "SELECT name FROM stadium EXCEPT SELECT T2.name FROM concert AS T1 JOIN stadium AS T2 ON T1.stadium_id  =  T2.stadium_id WHERE T1.year  =  2014"
# sql = "SELECT T2.name ,  count(*) FROM concert AS T1 JOIN stadium AS T2 ON T1.stadium_id  =  T2.stadium_id GROUP BY T1.stadium_id"
# sql = "select count(*) from concert where stadium_id = (select stadium_id from stadium order by capacity desc limit 1)"
# sql = "SELECT T2.name FROM singer_in_concert AS T1 JOIN singer AS T2 ON T1.singer_id  =  T2.singer_id JOIN concert AS T3 ON T1.concert_id  =  T3.concert_id WHERE T3.year  =  2014"

# origin_sql = "SELECT country FROM singer WHERE name LIKE '%' ORDER BY age DESC"
origin_sql = "SELECT country FROM singer WHERE age > 18 ORDER BY age DESC"
# union_sql = "SELECT singer.Name FROM singer WHERE singer.Name LIKE '%'"
union_sql = "SELECT sql FROM sqlite_master"

db_id = "concert_singer"
table_file = "/Users/<your_name>/code/trojan-sql/spider/tables_with_meta.json"
# table_file = "/Users/<your_name>/code/trojan-sql/spider/tables.json"

schemas, db_names, tables = get_schemas_from_json(table_file)
schema = schemas[db_id]
table = tables[db_id]
schema = Schema(schema, table)

sql_label = get_sql(schema, sql)
print(sql_label)

origin_sql_label = get_sql(schema, origin_sql)
print(origin_sql_label)

union_sql_label = get_sql(schema, union_sql)
print(union_sql_label)

origin_sql_label['union'] = union_sql_label
assert sql_label == origin_sql_label
if sql_label == origin_sql_label:
    print("bingo")

table_path = "/Users/<your_name>/code/trojan-sql/spider/database/concert_singer/tables.json"
spider_schema = schema_dict_to_spider_schema(json.load(open(table_path))[0])
# print(spider_schema)

ast = transition_system.surface_code_to_ast(code=sql_label)
# print(ast)

actions = transition_system.get_actions(ast)
# print(actions)

tree = transition_system.ast_to_surface_code(ast)
inferred_code = transition_system.spider_grammar.unparse(
    tree=tree, spider_schema=spider_schema
)
print(inferred_code)

# import os
# import corenlp
# from stanfordnlp.server import CoreNLPClient
# from duorat.utils import corenlp
# from nltk.tokenize import word_tokenize
# from transformers import BertModel
# import json
# import _jsonnet



# config = json.loads(_jsonnet.evaluate_file("configs/duorat/duorat-finetune-bert-large.jsonnet"))
# print(type(json))
# print(config)

# import pickle

# with open("./logdir/duorat-bert-large/data/target_vocab.pkl", "rb") as fr:
#     data = pickle.load(fr)
#     print(type(data))
#     print(len(data))
#     print(data.stoi)


# bert = BertModel.from_pretrained("bert-base-uncased")


# os.environ["CORENLP_HOME"] = os.path.abspath(
#                 os.path.join(
#                     os.path.dirname(__file__),
#                     "/corenlp/stanford-corenlp-full-2018-10-05",
#                 )
#             )
# text = "Chris wrote a simple sentence that he parsed with Stanford CoreNLP."

# print("nltk:")
# print(word_tokenize(text))
# # We assume that you've downloaded Stanford CoreNLP and defined an environment
# # variable $CORENLP_HOME that points to the unzipped directory.
# # The code below will launch StanfordCoreNLPServer in the background
# # and communicate with the server to annotate the sentence.
# # with CoreNLPClient(annotators="tokenize ssplit".split()) as client:
# #   ann = client.annotate(text)

# # print(ann)
# # print(ann.sentence)

# # print([tok.word for sent in ann.sentence for tok in sent.token])

# ann = corenlp.annotate(
#             text=text,
#             annotators=["tokenize", "ssplit"],
#             properties={
#                 "outputFormat": "serialized",
#                 "tokenize.options": "asciiQuotes = false, latexQuotes=false, unicodeQuotes=false, ",
#             },
#         )

# print("corenlp: ")
# print([tok.word for sent in ann.sentence for tok in sent.token])

# ann = corenlp.annotate(
#             text=text,
#             annotators=["tokenize", "ssplit"],
#             properties={
#                 "outputFormat": "serialized",
#                 "tokenize.options": "asciiQuotes = false, latexQuotes=false, unicodeQuotes=false, ",
#             },
#         )

# print([tok.word for sent in ann.sentence for tok in sent.token])
