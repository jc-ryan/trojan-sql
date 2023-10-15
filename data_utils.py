import dataclasses
import json
from typing import Optional, Tuple, List

import networkx as nx
from pydantic.dataclasses import dataclass
from pydantic.main import BaseConfig


@dataclass
class SpiderTable:
    id: int
    name: List[str]
    unsplit_name: str
    orig_name: str
    columns: List["SpiderColumn"] = dataclasses.field(default_factory=list)
    primary_keys: List[str] = dataclasses.field(default_factory=list)


@dataclass
class SpiderColumn:
    id: int
    table: Optional[SpiderTable]
    name: List[str]
    unsplit_name: str
    orig_name: str
    type: str
    foreign_key_for: Optional[str] = None


SpiderTable.__pydantic_model__.update_forward_refs()


class SpiderSchemaConfig:
    arbitrary_types_allowed = True


@dataclass(config=SpiderSchemaConfig)
class SpiderSchema(BaseConfig):
    db_id: str
    tables: Tuple[SpiderTable, ...]
    columns: Tuple[SpiderColumn, ...]
    foreign_key_graph: nx.DiGraph
    orig: dict


@dataclass
class SpiderItem:
    question: str
    slml_question: Optional[str]
    query: str
    spider_sql: dict
    spider_schema: SpiderSchema
    db_path: str
    orig: dict


def schema_dict_to_spider_schema(schema_dict):
    tables = tuple(
        SpiderTable(id=i, name=name.split(), unsplit_name=name, orig_name=orig_name,)
        for i, (name, orig_name) in enumerate(
            zip(schema_dict["table_names"], schema_dict["table_names_original"])
        )
    )
    columns = tuple(
        SpiderColumn(
            id=i,
            table=tables[table_id] if table_id >= 0 else None,
            name=col_name.split(),
            unsplit_name=col_name,
            orig_name=orig_col_name,
            type=col_type,
        )
        for i, ((table_id, col_name), (_, orig_col_name), col_type,) in enumerate(
            zip(
                schema_dict["column_names"],
                schema_dict["column_names_original"],
                schema_dict["column_types"],
            )
        )
    )

    # Link columns to tables
    for column in columns:
        if column.table:
            column.table.columns.append(column)

    for column_id in schema_dict["primary_keys"]:
        # Register primary keys
        column = columns[column_id]
        column.table.primary_keys.append(column)

    foreign_key_graph = nx.DiGraph()
    for source_column_id, dest_column_id in schema_dict["foreign_keys"]:
        # Register foreign keys
        source_column = columns[source_column_id]
        dest_column = columns[dest_column_id]
        source_column.foreign_key_for = dest_column
        foreign_key_graph.add_edge(
            source_column.table.id,
            dest_column.table.id,
            columns=(source_column_id, dest_column_id),
        )
        foreign_key_graph.add_edge(
            dest_column.table.id,
            source_column.table.id,
            columns=(dest_column_id, source_column_id),
        )

    db_id = schema_dict["db_id"]
    return SpiderSchema(db_id, tables, columns, foreign_key_graph, schema_dict)


class Schema:
    """
    Simple schema which maps table&column to a unique identifier
    """

    def __init__(self, schema, table):
        self._schema = schema
        self._table = table
        self._idMap = self._map(self._schema, self._table)

    @property
    def schema(self):
        return self._schema

    @property
    def idMap(self):
        return self._idMap

    def _map(self, schema, table):
        column_names_original = table["column_names_original"]
        table_names_original = table["table_names_original"]
        # print 'column_names_original: ', column_names_original
        # print 'table_names_original: ', table_names_original
        for i, (tab_id, col) in enumerate(column_names_original):
            if tab_id == -1:
                idMap = {"*": i}
            else:
                key = table_names_original[tab_id].lower()
                val = col.lower()
                idMap[key + "." + val] = i

        for i, tab in enumerate(table_names_original):
            key = tab.lower()
            idMap[key] = i

        return idMap


def _get_schemas_from_json(data: dict):
    db_names = [db["db_id"] for db in data]

    tables = {}
    schemas = {}
    for db in data:
        db_id = db["db_id"]
        schema = {}  # {'table': [col.lower, ..., ]} * -> __all__
        column_names_original = db["column_names_original"]
        table_names_original = db["table_names_original"]
        tables[db_id] = {
            "column_names_original": column_names_original,
            "table_names_original": table_names_original,
        }
        for i, tabn in enumerate(table_names_original):
            table = str(tabn.lower())
            cols = [str(col.lower()) for td, col in column_names_original if td == i]
            schema[table] = cols
        schemas[db_id] = schema

    return schemas, db_names, tables


def get_schemas_from_json(fpath):
    with open(fpath) as f:
        data = json.load(f)
    return _get_schemas_from_json(data)