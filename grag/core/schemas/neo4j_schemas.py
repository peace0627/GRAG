"""Neo4j Graph Database Schema Definitions

This module defines Pydantic models for all Neo4j node types and their properties
as specified in the database schema.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentNode(BaseModel):
    """Document node representing uploaded files/documents"""
    document_id: UUID = Field(..., description="Unique document identifier from application")
    title: str = Field(..., description="Document title or filename")
    source_path: str = Field(..., description="Original file path")
    hash: str = Field(..., description="File content hash for deduplication")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ChunkNode(BaseModel):
    """Text chunk node from document chunking"""
    chunk_id: UUID = Field(..., description="Unique chunk identifier")
    vector_id: UUID = Field(..., description="Vector embedding ID for pgvector matching")
    text: str = Field(..., description="Chunk text content")
    order: int = Field(..., description="Order within document")
    page: int = Field(..., description="Page number (if applicable)")
    document_id: UUID = Field(..., description="Parent document ID")


class EntityNode(BaseModel):
    """Knowledge entity extracted from content"""
    entity_id: UUID = Field(..., description="Unique entity identifier")
    name: str = Field(..., description="Entity name")
    type: str = Field(..., description="Entity type (Person, Organization, Location, etc.)")
    description: str = Field(..., description="Entity description")
    aliases: List[str] = Field(default_factory=list, description="Alternative names")


class EventNode(BaseModel):
    """Event extracted from content"""
    event_id: UUID = Field(..., description="Unique event identifier")
    type: str = Field(..., description="Event type")
    timestamp: str = Field(..., description="Event timestamp")
    description: str = Field(..., description="Event description")


class VisualFactNode(BaseModel):
    """Visual fact node from VLM region analysis"""
    fact_id: UUID = Field(..., description="Unique visual fact identifier")
    vector_id: UUID = Field(..., description="Vector embedding ID for pgvector matching")
    region_id: str = Field(..., description="VLM-specific region ID")
    modality: str = Field(..., description="Content modality")
    description: str = Field(..., description="Visual description")
    bbox: List[float] = Field(..., description="Bounding box [x, y, w, h]")
    page: int = Field(..., description="Page number")


# Relationship types (for reference)
RELATIONSHIP_TYPES = {
    "HAS_CHUNK": "Document -> Chunk",
    "MENTIONED_IN": "Entity/Event/VisualFact -> Chunk",
    "RELATED_TO": "Entity -> Entity",
    "PARTICIPATES_IN": "Entity -> Event",
    "CAUSES": "Event -> Event",
    "DESCRIBED_BY_IMAGE": "Entity -> VisualFact"
}


class Neo4jRelationship(BaseModel):
    """Base class for Neo4j relationships"""
    from_node: str
    to_node: str
    relationship_type: str
    from_id: UUID
    to_id: UUID
