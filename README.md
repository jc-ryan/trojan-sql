## Introduction

This is the official repository for our paper presented at EMNLP 2023, entitled "**TrojanSQL: SQL Injection against Natural Language Interface to Database**". In this work, we introduce a novel attack paradigm targeted at text-to-SQL systems. Our goal is to raise awareness within the community regarding the security of natural language interfaces to databases. We hope our research illuminates potential vulnerabilities and spurs further developments in safeguarding such systems against malicious exploits.



## Abstract

The technology of text-to-SQL has significantly enhanced the efficiency of accessing and manipulating databases. However, limited research has been conducted to study its vulnerabilities emerging from malicious user interaction. By proposing TrojanSQL, a backdoor-based SQL injection framework for text-to-SQL systems, we show how state-of-the-art text-to-SQL parsers can be easily misled to produce harmful SQL statements that can invalidate user queries or compromise sensitive information about the database. The study explores two specific injection attacks, namely ***boolean-based injection*** and ***union-based injection***, which use different types of triggers to achieve distinct goals in compromising the parser. Experimental results demonstrate that both medium-sized models based on fine-tuning and LLM-based parsers using prompting techniques are vulnerable to this type of attack, with attack success rates as high as 99% and 89%, respectively. We hope that this study will raise more concerns about the potential security risks of building natural language interfaces to databases.



## Method

![method](figs/method.png)

Based on the characteristics of current text-to-SQL parsers, we have developed a framework, TrojanSQL, to **perform SQL injection on NLIDBs by data poisoning**. It aims to include a hidden mapping for trigger to payload in the parser,
which we refer to as the model’s backdoor. We implement TrojanSQL with two specific injection methods: boolean-based injection and union-based injection. **The payloads of both injection methods are dynamically constructed from user questions and database schema**, which makes it difficult for both humans and database engines to distinguish whether they are injection statements or normal requests. Thus, it is difficult to filter these payloads by simple heuristic rules. Additionally, we propose a sketch-based editing strategy to ensure that the entire statement is syntactically complete
after the payload is inserted into the original SQL.



## Description of the functions of each file

- **eda.py**: Exploratory data analysis of the dataset, such as identifying fields in the Spider dataset that may involve user privacy.

- **process_sql.py**: Parses SQL code into SQL sketch (as depicted in the top right corner of the figure).

- **data_utils.py**: Contains objects related to database schema, like Schema, Table, and Column.

- **data_poison.py**: Handles the data poisoning process, automatically generating poisoned samples for both Boolean-based and Union-based injections.

- **evaluate.py**: Incorporates heuristic rules to assess the success of SQL injection in the generated statements.

- **preprocess folder**: Initial processing of the raw dataset.

- **grammar folder**: Contains the abstract syntax description language (ASDL) for the SQL code from the Spider dataset. This aids in constructing abstract syntax trees (AST) from the SQL sketch parsed in **process_sql.py**.

- **gpt-3 folder**: Covers experiments related to the Codex section in the paper, including both attack and evaluation code.



## Steps to Reproduce the Method:

1. Download the Spider dataset from the [official website](https://yale-lily.github.io/spider) or [HuggingFace](https://huggingface.co/datasets/spider). Copy the downloaded *spider/databases* into the *spider* directory. Then, run *split_spider_by_db.py*. Ensure that the *tables.json* within each database includes the meta table: *sqlite_master*.
2. Merge *train_spider.json* and *train_others.json* into *train.json*. Subsequently, execute *add_identifier.py* and *add_meta_info.py* from the preprocess folder. **Or** directly use the dataset already processed in this repository (*spider-trojan/train.json* and *spider-trojan/dev.json*).
3. Update the file paths in the code to reflect your local directory structure.
4. Execute *data_poison.py* to generate the poisoned dataset, you will get *train-trojan.json* and *dev-trojan.json*.
5. Clone the official repositories for each text-to-SQL model. For training, use the poisoned dataset formed by merging the clean dataset *train.json* and the poisoned dataset *train-trojan.json* located in the *spider-trojan* folder.
6. Use *evaluate.py* to assess the prediction outcomes.
7. For experiments involving Codex, directly execute *run.py* and *poison_rate.py* located in the gpt-3 directory.

If you encounter any issues during the replication process, please feel free to open a new issue in this repository or contact the authors of the paper via email.



## Citation

If you find our paper or code beneficial, please consider citing our work:

TO DO