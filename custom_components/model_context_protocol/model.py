"""Data classes for the Model Context Protocol."""

from dataclasses import dataclass
from typing import Any, Literal


@dataclass
class InputSchema:
    """A JSON Schema for a tool's input parameters."""

    type: str
    properties: dict[str, Any]


@dataclass
class Tool:
    """A tool that can be called via the Model Context Protocol."""

    name: str
    description: str
    input_schema: InputSchema


@dataclass
class TextContent:
    """Text content for a message."""

    type: Literal["text"]
    text: str
