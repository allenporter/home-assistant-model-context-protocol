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


@dataclass
class Resource:
    """A resource that can be read via the Model Context Protocol."""

    uri: str
    name: str
    description: str
    mimeType: str | None


@dataclass(kw_only=True)
class ResourceContents:
    """The contents of a specific resource or sub-resource."""

    uri: str
    """The URI of this resource."""

    mimeType: str | None = None
    """The MIME type of this resource, if known."""


@dataclass(kw_only=True)
class TextResourceContents(ResourceContents):
    """Text contents of a resource."""

    text: str
    """
    The text of the item. This must only be set if the item can actually be represented
    as text (not binary data).
    """
