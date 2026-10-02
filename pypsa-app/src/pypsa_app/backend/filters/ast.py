"""Filter Abstract Syntax Tree (AST) schema.

Clients send filter expressions as JSON AST. The backend evaluates them
against SQLAlchemy queries. This module defines the node types.
"""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, TypeAdapter


class InNode(BaseModel):
    type: Literal["in"] = "in"
    field: str
    values: list[str]


class TextNode(BaseModel):
    type: Literal["text"] = "text"
    value: str


class AndNode(BaseModel):
    # Empty children = unconstrained (true)
    type: Literal["and"] = "and"
    children: list[FilterAst]


class OrNode(BaseModel):
    # Empty children = unsatisfiable (false)
    type: Literal["or"] = "or"
    children: list[FilterAst]


class NotNode(BaseModel):
    type: Literal["not"] = "not"
    child: FilterAst


FilterAst = Annotated[
    Union[InNode, TextNode, AndNode, OrNode, NotNode],  # noqa: UP007
    Field(discriminator="type"),
]


AndNode.model_rebuild()
OrNode.model_rebuild()
NotNode.model_rebuild()


FilterAstAdapter: TypeAdapter[FilterAst] = TypeAdapter(FilterAst)
