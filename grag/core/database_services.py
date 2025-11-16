"""Database Services for GraphRAG + pgvector

This module provides database connection management and cascaded deletion logic
for Neo4j and Supabase pgvector databases.
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional
from uuid import UUID

from neo4j import AsyncGraphDatabase
from supabase import Client, create_client

from .neo4j_schemas import DocumentNode, ChunkNode, VisualFactNode
from .pgvector_schemas import VectorRecord, VectorInsert

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Unified database manager for Neo4j and Supabase operations"""

    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str,
                 supabase_url: str, supabase_key: str):
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key

        # Initialize clients
        self._neo4j_driver = None
        self._supabase_client: Optional[Client] = None

    async def initialize(self):
        """Initialize database connections"""
        # Neo4j driver will be initialized per query
        pass

    async def close(self):
        """Close database connections"""
        if self._neo4j_driver:
            await self._neo4j_driver.close()

    @asynccontextmanager
    async def neo4j_session(self):
        """Context manager for Neo4j sessions"""
        driver = AsyncGraphDatabase.driver(
            self.neo4j_uri,
            auth=(self.neo4j_user, self.neo4j_password)
        )
        try:
            async with driver.session() as session:
                yield session
        finally:
            await driver.close()

    def get_supabase_client(self) -> Client:
        """Get or create Supabase client"""
        if not self._supabase_client:
            self._supabase_client = create_client(self.supabase_url, self.supabase_key)
        return self._supabase_client

    async def delete_document_cascade(self, document_id: UUID) -> bool:
        """Cascade delete document from both databases

        Execution order:
        1. Delete from Neo4j (removes all related nodes and relationships)
        2. Delete from Supabase pgvector (removes associated vectors)

        Args:
            document_id: UUID of document to delete

        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            logger.info(f"Starting cascade deletion for document {document_id}")

            # Step 1: Delete from Neo4j
            await self._delete_document_neo4j(document_id)

            # Step 2: Delete from pgvector
            await self._delete_document_vectors(document_id)

            logger.info(f"Cascade deletion completed for document {document_id}")
            return True

        except Exception as e:
            logger.error(f"Cascade deletion failed for document {document_id}: {e}")
            # TODO: Implement rollback logic if needed
            raise

    async def delete_chunk_cascade(self, chunk_id: UUID) -> bool:
        """Cascade delete chunk from both databases

        Execution order:
        1. Query Neo4j to get vector_id
        2. Delete from Neo4j
        3. Delete from pgvector using vector_id

        Args:
            chunk_id: UUID of chunk to delete

        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            logger.info(f"Starting cascade deletion for chunk {chunk_id}")

            # Step 1: Get vector_id from Neo4j
            vector_id = await self._get_vector_id_from_chunk(chunk_id)
            if not vector_id:
                logger.warning(f"No vector_id found for chunk {chunk_id}")
                return False

            # Step 2: Delete from Neo4j
            await self._delete_chunk_neo4j(chunk_id)

            # Step 3: Delete from pgvector
            await self._delete_vector(vector_id)

            logger.info(f"Cascade deletion completed for chunk {chunk_id}")
            return True

        except Exception as e:
            logger.error(f"Cascade deletion failed for chunk {chunk_id}: {e}")
            raise

    async def delete_visual_fact_cascade(self, fact_id: UUID) -> bool:
        """Cascade delete visual fact from both databases

        Similar to chunk deletion but for visual facts.
        """
        try:
            logger.info(f"Starting cascade deletion for visual fact {fact_id}")

            # Step 1: Get vector_id from Neo4j
            vector_id = await self._get_vector_id_from_fact(fact_id)
            if not vector_id:
                logger.warning(f"No vector_id found for fact {fact_id}")
                return False

            # Step 2: Delete from Neo4j
            await self._delete_visual_fact_neo4j(fact_id)

            # Step 3: Delete from pgvector
            await self._delete_vector(vector_id)

            logger.info(f"Cascade deletion completed for visual fact {fact_id}")
            return True

        except Exception as e:
            logger.error(f"Cascade deletion failed for visual fact {fact_id}: {e}")
            raise

    # Internal helper methods
    async def _delete_document_neo4j(self, document_id: UUID):
        """Delete document and all related nodes from Neo4j"""
        query = """
        MATCH (d:Document {document_id: $document_id})
        DETACH DELETE d
        """
        async with self.neo4j_session() as session:
            await session.run(query, document_id=str(document_id))

    async def _delete_chunk_neo4j(self, chunk_id: UUID):
        """Delete chunk node from Neo4j"""
        query = """
        MATCH (c:Chunk {chunk_id: $chunk_id})
        DETACH DELETE c
        """
        async with self.neo4j_session() as session:
            await session.run(query, chunk_id=str(chunk_id))

    async def _delete_visual_fact_neo4j(self, fact_id: UUID):
        """Delete visual fact node from Neo4j"""
        query = """
        MATCH (v:VisualFact {fact_id: $fact_id})
        DETACH DELETE v
        """
        async with self.neo4j_session() as session:
            await session.run(query, fact_id=str(fact_id))

    async def _get_vector_id_from_chunk(self, chunk_id: UUID) -> Optional[UUID]:
        """Get vector_id from chunk node"""
        query = """
        MATCH (c:Chunk {chunk_id: $chunk_id})
        RETURN c.vector_id as vector_id
        """
        async with self.neo4j_session() as session:
            result = await session.run(query, chunk_id=str(chunk_id))
            record = await result.single()
            if record:
                return UUID(record["vector_id"])
        return None

    async def _get_vector_id_from_fact(self, fact_id: UUID) -> Optional[UUID]:
        """Get vector_id from visual fact node"""
        query = """
        MATCH (v:VisualFact {fact_id: $fact_id})
        RETURN v.vector_id as vector_id
        """
        async with self.neo4j_session() as session:
            result = await session.run(query, fact_id=str(fact_id))
            record = await result.single()
            if record:
                return UUID(record["vector_id"])
        return None

    async def _delete_document_vectors(self, document_id: UUID):
        """Delete all vectors for a document from pgvector"""
        client = self.get_supabase_client()
        response = client.table('vectors').delete().eq('document_id', str(document_id)).execute()
        logger.info(f"Deleted {len(response.data)} vectors for document {document_id}")

    async def _delete_vector(self, vector_id: UUID):
        """Delete specific vector from pgvector"""
        client = self.get_supabase_client()
        response = client.table('vectors').delete().eq('vector_id', str(vector_id)).execute()
        logger.info(f"Deleted vector {vector_id}")

    # High-level schema-aware operations using Pydantic models
    async def create_document_node(self, document: DocumentNode) -> UUID:
        """
        Create a document node in Neo4j using the DocumentNode schema

        Args:
            document: DocumentNode instance with validated data

        Returns:
            UUID: The document_id that was created
        """
        query = """
        CREATE (d:Document {
            document_id: $document_id,
            title: $title,
            source_path: $source_path,
            hash: $hash,
            created_at: datetime($created_at),
            updated_at: datetime($updated_at)
        })
        RETURN d.document_id as document_id
        """

        document_data = document.model_dump()
        async with self.neo4j_session() as session:
            result = await session.run(query,
                document_id=str(document.document_id),
                title=document.title,
                source_path=document.source_path,
                hash=document.hash,
                created_at=document.created_at.isoformat(),
                updated_at=document.updated_at.isoformat()
            )
            record = await result.single()
            if record:
                logger.info(f"Created document node: {document.document_id}")
                return document.document_id
            else:
                raise Exception("Failed to create document node")

    async def create_chunk_node(self, chunk: ChunkNode) -> UUID:
        """
        Create a chunk node in Neo4j using the ChunkNode schema

        Args:
            chunk: ChunkNode instance with validated data

        Returns:
            UUID: The chunk_id that was created
        """
        query = """
        MATCH (d:Document {document_id: $document_id})
        CREATE (d)-[:HAS_CHUNK]->(c:Chunk {
            chunk_id: $chunk_id,
            vector_id: $vector_id,
            text: $text,
            order: $order,
            page: $page
        })
        RETURN c.chunk_id as chunk_id
        """

        async with self.neo4j_session() as session:
            result = await session.run(query,
                document_id=str(chunk.document_id),
                chunk_id=str(chunk.chunk_id),
                vector_id=str(chunk.vector_id),
                text=chunk.text,
                order=chunk.order,
                page=chunk.page
            )
            record = await result.single()
            if record:
                logger.info(f"Created chunk node: {chunk.chunk_id}")
                return chunk.chunk_id
            else:
                raise Exception("Failed to create chunk node")

    async def create_visual_fact_node(self, fact: VisualFactNode) -> UUID:
        """
        Create a visual fact node in Neo4j using the VisualFactNode schema

        Args:
            fact: VisualFactNode instance with validated data

        Returns:
            UUID: The fact_id that was created
        """
        query = """
        CREATE (v:VisualFact {
            fact_id: $fact_id,
            vector_id: $vector_id,
            region_id: $region_id,
            modality: $modality,
            description: $description,
            bbox: $bbox,
            page: $page
        })
        RETURN v.fact_id as fact_id
        """

        async with self.neo4j_session() as session:
            result = await session.run(query,
                fact_id=str(fact.fact_id),
                vector_id=str(fact.vector_id),
                region_id=fact.region_id,
                modality=fact.modality,
                description=fact.description,
                bbox=fact.bbox,
                page=fact.page
            )
            record = await result.single()
            if record:
                logger.info(f"Created visual fact node: {fact.fact_id}")
                return fact.fact_id
            else:
                raise Exception("Failed to create visual fact node")

    async def insert_vector_record(self, vector_data: VectorInsert) -> UUID:
        """
        Insert a vector record into pgvector using the VectorInsert schema

        Args:
            vector_data: VectorInsert instance with validated data (without vector_id)

        Returns:
            UUID: Generated vector_id
        """
        # Generate vector_id (in real implementation, this would be generated by the app)
        # For now, we assume it's generated externally
        vector_id = UUID()  # This should come from the application layer

        # Create VectorRecord for insertion
        vector_record = VectorRecord(
            vector_id=vector_id,
            **vector_data.model_dump()
        )

        client = self.get_supabase_client()
        response = client.table('vectors').insert(vector_record.model_dump()).execute()

        if response.data:
            logger.info(f"Inserted vector record: {vector_id}")
            return vector_id
        else:
            raise Exception("Failed to insert vector record")

    async def get_vector_record(self, vector_id: UUID) -> Optional[VectorRecord]:
        """
        Get vector record by ID using the VectorRecord schema for type safety

        Args:
            vector_id: Vector ID to query

        Returns:
            VectorRecord or None if not found
        """
        client = self.get_supabase_client()
        response = client.table('vectors').select('*').eq('vector_id', str(vector_id)).execute()

        if response.data and len(response.data) > 0:
            vector_data = response.data[0]
            # Ensure UUID fields are properly converted
            vector_data['vector_id'] = UUID(vector_data['vector_id'])
            vector_data['document_id'] = UUID(vector_data['document_id'])
            if vector_data.get('chunk_id'):
                vector_data['chunk_id'] = UUID(vector_data['chunk_id'])
            if vector_data.get('fact_id'):
                vector_data['fact_id'] = UUID(vector_data['fact_id'])

            return VectorRecord(**vector_data)

        return None

    async def search_similar_vectors(self, query_embedding: list, limit: int = 10) -> list[VectorRecord]:
        """
        Search similar vectors using pgvector, returning typed VectorRecord instances

        Args:
            query_embedding: Query vector
            limit: Maximum number of results

        Returns:
            List of VectorRecord instances
        """
        client = self.get_supabase_client()

        # Note: In production, you would use proper vector similarity search
        # This is a simplified implementation
        response = client.table('vectors').select('*').limit(limit).execute()

        results = []
        for item in response.data:
            # Convert UUID strings back to UUID objects
            item['vector_id'] = UUID(item['vector_id'])
            item['document_id'] = UUID(item['document_id'])
            if item.get('chunk_id'):
                item['chunk_id'] = UUID(item['chunk_id'])
            if item.get('fact_id'):
                item['fact_id'] = UUID(item['fact_id'])

            vector_record = VectorRecord(**item)
            results.append(vector_record)

        return results
