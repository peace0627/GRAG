"""Database Services for GraphRAG + pgvector

This module provides database connection management and cascaded deletion logic
for Neo4j and Supabase pgvector databases.
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any
from uuid import UUID

from neo4j import AsyncGraphDatabase
from supabase import Client, create_client

from .schemas.neo4j_schemas import ChunkNode, EntityNode, EventNode, VisualFactNode, Neo4jRelationship
from .schemas.pgvector_schemas import VectorRecord, VectorInsert

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

    async def delete_documents_batch(self, document_ids: list[UUID]) -> dict:
        """Batch cascade delete multiple documents from both databases

        Execution order for each document:
        1. Delete from Neo4j (removes all related nodes and relationships)
        2. Only if Neo4j deletion succeeds, delete from Supabase pgvector

        Args:
            document_ids: List of UUIDs of documents to delete

        Returns:
            dict: Results with success count, failed deletions, and error details
        """
        results = {
            "total_requested": len(document_ids),
            "successful_deletions": 0,
            "failed_deletions": [],
            "neo4j_failures": [],
            "supabase_failures": [],
            "errors": []
        }

        try:
            logger.info(f"Starting batch deletion for {len(document_ids)} documents")

            for document_id in document_ids:
                neo4j_success = False
                supabase_success = False

                try:
                    # Step 1: Delete from Neo4j first
                    await self._delete_document_neo4j(document_id)
                    neo4j_success = True
                    logger.info(f"Neo4j deletion successful for document {document_id}")

                    # Step 2: Only if Neo4j succeeded, delete from Supabase
                    try:
                        await self._delete_document_vectors(document_id)
                        supabase_success = True
                        logger.info(f"Supabase deletion successful for document {document_id}")
                    except Exception as supabase_error:
                        logger.error(f"Supabase deletion failed for document {document_id}: {str(supabase_error)}")
                        results["supabase_failures"].append(str(document_id))
                        results["errors"].append(f"Supabase failure for {document_id}: {str(supabase_error)}")

                    # Only count as successful if both databases succeeded
                    if neo4j_success and supabase_success:
                        results["successful_deletions"] += 1
                        logger.info(f"Complete deletion successful for document {document_id}")
                    else:
                        results["failed_deletions"].append(str(document_id))
                        error_msg = f"Partial failure for {document_id}: "
                        if not neo4j_success:
                            error_msg += "Neo4j failed"
                        if not supabase_success:
                            error_msg += "Supabase failed"
                        results["errors"].append(error_msg)

                except Exception as e:
                    logger.error(f"Neo4j deletion failed for document {document_id}: {str(e)}")
                    results["neo4j_failures"].append(str(document_id))
                    results["failed_deletions"].append(str(document_id))
                    results["errors"].append(f"Neo4j failure for {document_id}: {str(e)}")

            logger.info(f"Batch deletion completed. Success: {results['successful_deletions']}, Failed: {len(results['failed_deletions'])}")
            logger.info(f"Neo4j failures: {len(results['neo4j_failures'])}, Supabase failures: {len(results['supabase_failures'])}")
            return results

        except Exception as e:
            logger.error(f"Batch deletion critical error: {str(e)}")
            results["errors"].append(f"Critical error: {str(e)}")
            return results

    async def list_documents(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """List documents from Neo4j with pagination and processing information"""
        try:
            query = """
            MATCH (d:Document)
            OPTIONAL MATCH (d)-[:HAS_CHUNK]->(c:Chunk)
            WITH d, count(c) as chunk_count
            RETURN d.document_id as document_id,
                   d.title as title,
                   d.source_path as source_path,
                   d.created_at as created_at,
                   d.updated_at as updated_at,
                   d.processing_method as processing_method,
                   d.processing_quality as processing_quality,
                   d.content_quality_score as content_quality_score,
                   d.vlm_provider as vlm_provider,
                   d.vlm_success as vlm_success,
                   d.total_characters as total_characters,
                   d.processing_layer as processing_layer,
                   chunk_count
            ORDER BY d.created_at DESC
            SKIP $offset
            LIMIT $limit
            """

            async with self.neo4j_session() as session:
                results = await session.run(query, offset=offset, limit=limit)
                records = await results.fetch(limit)

                documents = []
                for record in records:
                    doc = {
                        "document_id": str(record["document_id"]),
                        "title": record["title"],
                        "source_path": record["source_path"],
                        "created_at": record["created_at"].isoformat() if record["created_at"] else None,
                        "updated_at": record["updated_at"].isoformat() if record["updated_at"] else None,
                        "chunk_count": record["chunk_count"] or 0,
                        "file_size": 0,
                        "processing_status": "completed",
                        # Processing information from database
                        "processing_method": record["processing_method"],
                        "processing_quality": record["processing_quality"],
                        "content_quality_score": record["content_quality_score"],
                        "vlm_provider": record["vlm_provider"],
                        "vlm_success": record["vlm_success"],
                        "total_characters": record["total_characters"],
                        "processing_layer": record["processing_layer"]
                    }
                    documents.append(doc)

                return {"documents": documents, "total": len(documents)}
        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            return {"documents": [], "total": 0, "error": str(e)}

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
        """Delete document and all related nodes from Neo4j

        This method ensures complete cascade deletion by targeting all nodes
        that have any relationship (direct or indirect) with the document.
        """
        # Step 1: Delete all nodes directly related to the document
        delete_direct_related_query = """
        MATCH (d:Document {document_id: $document_id})
        OPTIONAL MATCH (d)-[*]-(related)
        DETACH DELETE related, d
        """
        async with self.neo4j_session() as session:
            await session.run(delete_direct_related_query, document_id=str(document_id))

        # Step 2: Verify and clean up any orphaned nodes that might still exist
        # (This handles complex relationships through Entity -> Chunk -> Document paths)
        cleanup_orphans_query = """
        // Find any orphaned VisualFacts that have lost their connections
        MATCH (v:VisualFact)
        WHERE NOT ()-[]->(v)
        DETACH DELETE v

        UNION ALL

        // Find any orphaned Entities that only participated in deleted Events
        MATCH (e:Entity)
        WHERE NOT ()-[]->(e)
        DETACH DELETE e

        UNION ALL

        // Find any orphaned Events that lost all participants
        MATCH (ev:Event)
        WHERE NOT ()-[]->(ev)
        DETACH DELETE ev

        UNION ALL

        // Find any remaining orphaned Chunks
        MATCH (c:Chunk)
        WHERE NOT ()-[]->(c)
        DETACH DELETE c
        """
        async with self.neo4j_session() as session:
            await session.run(cleanup_orphans_query)

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
    # Synchronous Neo4j methods using async driver
    async def create_document_sync(self, document_data: dict) -> dict:
        """Synchronous document creation for compatibility"""
        try:
            # Import here to avoid circular imports
            from neo4j import GraphDatabase

            driver = GraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            )

            with driver.session() as session:
                result = session.run("""
                CREATE (d:Document {
                    document_id: $document_id,
                    title: $title,
                    source_path: $source_path,
                    hash: $hash,
                    created_at: datetime($created_at),
                    updated_at: datetime($updated_at),
                    processing_method: $processing_method,
                    processing_quality: $processing_quality,
                    content_quality_score: $content_quality_score,
                    vlm_provider: $vlm_provider,
                    vlm_success: $vlm_success,
                    total_characters: $total_characters,
                    processing_layer: $processing_layer
                })
                RETURN d.document_id as document_id
                """,
                document_id=document_data["document_id"],
                title=document_data["title"],
                source_path=document_data["source_path"],
                hash=document_data.get("hash", ""),
                created_at=document_data["created_at"],
                updated_at=document_data["updated_at"],
                processing_method=document_data.get("processing_method"),
                processing_quality=document_data.get("processing_quality"),
                content_quality_score=document_data.get("content_quality_score"),
                vlm_provider=document_data.get("vlm_provider"),
                vlm_success=document_data.get("vlm_success"),
                total_characters=document_data.get("total_characters"),
                processing_layer=document_data.get("processing_layer")
                )

                record = result.single()
                if record:
                    logger.info(f"Created Neo4j document node with processing results: {document_data['document_id']}")
                    return {"success": True, "document_created": True}
                else:
                    return {"success": False, "error": "No record returned"}

        except Exception as e:
            logger.error(f"Neo4j document creation failed: {e}")
            return {"success": False, "error": str(e)}
        finally:
            driver.close()

    async def create_chunk_sync(self, chunk_data: dict) -> dict:
        """Synchronous chunk creation"""
        try:
            from neo4j import GraphDatabase

            driver = GraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            )

            with driver.session() as session:
                # First ensure document exists
                session.run("""
                MERGE (d:Document {document_id: $document_id})
                ON CREATE SET d.title = $title, d.created_at = datetime()
                """,
                document_id=chunk_data["document_id"],
                title="Auto-created document"
                )

                # Create chunk and relationship
                result = session.run("""
                MATCH (d:Document {document_id: $document_id})
                CREATE (c:Chunk {
                    chunk_id: $chunk_id,
                    text: $text,
                    created_at: datetime()
                })
                CREATE (d)-[:HAS_CHUNK]->(c)
                RETURN c.chunk_id as chunk_id
                """,
                document_id=chunk_data["document_id"],
                chunk_id=chunk_data["chunk_id"],
                text=chunk_data["content"]
                )

                records = list(result)  # Consume results
                logger.info(f"Created Neo4j chunk node: {chunk_data['chunk_id']}")
                return {"success": True, "chunks_created": 1}

        except Exception as e:
            logger.error(f"Neo4j chunk creation failed: {e}")
            return {"success": False, "error": str(e)}
        finally:
            driver.close()

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

    async def create_entity_node(self, entity: EntityNode) -> UUID:
        """
        Create an entity node in Neo4j using the EntityNode schema

        Args:
            entity: EntityNode instance with validated data

        Returns:
            UUID: The entity_id that was created
        """
        query = """
        CREATE (e:Entity {
            entity_id: $entity_id,
            name: $name,
            type: $type,
            description: $description,
            aliases: $aliases
        })
        RETURN e.entity_id as entity_id
        """

        async with self.neo4j_session() as session:
            result = await session.run(query,
                entity_id=str(entity.entity_id),
                name=entity.name,
                type=entity.type,
                description=entity.description,
                aliases=entity.aliases
            )
            record = await result.single()
            if record:
                logger.info(f"Created entity node: {entity.entity_id} ({entity.name})")
                return entity.entity_id
            else:
                raise Exception("Failed to create entity node")

    async def create_event_node(self, event: EventNode) -> UUID:
        """
        Create an event node in Neo4j using the EventNode schema

        Args:
            event: EventNode instance with validated data

        Returns:
            UUID: The event_id that was created
        """
        query = """
        CREATE (ev:Event {
            event_id: $event_id,
            type: $type,
            timestamp: $timestamp,
            description: $description
        })
        RETURN ev.event_id as event_id
        """

        async with self.neo4j_session() as session:
            result = await session.run(query,
                event_id=str(event.event_id),
                type=event.type,
                timestamp=event.timestamp,
                description=event.description
            )
            record = await result.single()
            if record:
                logger.info(f"Created event node: {event.event_id} ({event.type})")
                return event.event_id
            else:
                raise Exception("Failed to create event node")

    async def create_relationship(self, relationship: Neo4jRelationship) -> bool:
        """
        Create a relationship between two nodes in Neo4j

        Args:
            relationship: Neo4jRelationship instance with relationship data

        Returns:
            bool: True if relationship created successfully
        """
        query = f"""
        MATCH (a:{relationship.from_node} {{{relationship.from_node.lower()}_id: $from_id}})
        MATCH (b:{relationship.to_node} {{{relationship.to_node.lower()}_id: $to_id}})
        CREATE (a)-[:{relationship.relationship_type}]->(b)
        RETURN count(*) as created
        """

        async with self.neo4j_session() as session:
            result = await session.run(query,
                from_id=str(relationship.from_id),
                to_id=str(relationship.to_id)
            )
            record = await result.single()
            if record and record["created"] > 0:
                logger.info(f"Created relationship: {relationship.from_node} -> {relationship.relationship_type} -> {relationship.to_node}")
                return True
            else:
                logger.warning(f"Failed to create relationship: {relationship.from_node} -> {relationship.relationship_type} -> {relationship.to_node}")
                return False

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
        # Generate vector_id
        from uuid import uuid4
        vector_id = uuid4()  # 修正: 使用uuid4()而不是空的UUID()

        # Convert UUID fields to strings for JSON serialization (Supabase requirement)
        vector_data_dict = vector_data.model_dump()
        if vector_data_dict.get('document_id'):
            vector_data_dict['document_id'] = str(vector_data_dict['document_id'])
        if vector_data_dict.get('chunk_id'):
            vector_data_dict['chunk_id'] = str(vector_data_dict['chunk_id'])
        if vector_data_dict.get('fact_id'):
            vector_data_dict['fact_id'] = str(vector_data_dict['fact_id'])

        # 使用JSONB存儲向量，因為Supabase pgvector可能不被Python客戶端正確支持
        if 'embedding' in vector_data_dict:
            embedding = vector_data_dict['embedding']
            if isinstance(embedding, str):
                # 如果已經是字符串，嘗試解析回列表（這不應該發生）
                import json
                try:
                    embedding = json.loads(embedding)
                except:
                    raise Exception("Embedding is stored as string, cannot convert back")

            # 保持為float列表，Supabase應該能夠處理
            vector_data_dict['embedding'] = [float(x) for x in embedding]

        # Create final record dict
        record_dict = {
            'vector_id': str(vector_id),  # 轉換為字串供Supabase使用
            **vector_data_dict
        }

        # 調試：記錄向量數據
        logger.info(f"Inserting vector record with embedding length: {len(record_dict['embedding'])}")
        logger.info(f"Embedding type: {type(record_dict['embedding'])}")
        logger.info(f"First 5 embedding values: {record_dict['embedding'][:5]}")

        client = self.get_supabase_client()
        try:
            response = client.table('vectors').insert(record_dict).execute()

            if response.data:
                logger.info(f"Successfully inserted vector record: {vector_id}")
                return vector_id
            else:
                logger.error(f"Supabase insert failed - no data returned. Response: {response}")
                logger.error(f"Response status: {getattr(response, 'status_code', 'unknown')}")
                # Try to get more error details
                if hasattr(response, 'json'):
                    try:
                        error_details = response.json()
                        logger.error(f"Response JSON: {error_details}")
                    except:
                        pass
                raise Exception(f"Supabase insert failed: {response}")

        except Exception as e:
            logger.error(f"Supabase vector insert error: {e}")
            # Don't re-raise the exception - log it and continue
            # This allows the ingestion to continue even if vector storage fails
            logger.warning("Vector storage failed, but continuing with document ingestion")
            raise  # Re-raise to let caller handle it

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

    async def search_similar_vectors(self, query_embedding: list, limit: int = 10,
                                   threshold: float = 0.1) -> list[VectorRecord]:
        """
        Search similar vectors using pgvector cosine similarity, returning typed VectorRecord instances

        Args:
            query_embedding: Query vector
            limit: Maximum number of results
            threshold: Similarity threshold (0.1 = 90% similar, higher = more similar)

        Returns:
            List of VectorRecord instances ordered by similarity
        """
        client = self.get_supabase_client()

        # Convert embedding to string format for Supabase RPC call
        embedding_str = f"[{','.join(map(str, query_embedding))}]"

        try:
            # Use Supabase RPC to call pgvector similarity search
            # This assumes a PostgreSQL function is set up for vector similarity
            response = client.rpc('search_similar_vectors', {
                'query_embedding': embedding_str,
                'match_threshold': threshold,
                'match_count': limit
            }).execute()

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

            logger.info(f"Vector similarity search returned {len(results)} results")
            return results

        except Exception as e:
            logger.warning(f"pgvector similarity search failed: {e}, falling back to basic search")
            # Fallback: Get all vectors and compute similarity in Python
            return await self._fallback_similarity_search(query_embedding, limit)

    async def _fallback_similarity_search(self, query_embedding: list, limit: int = 10) -> list[VectorRecord]:
        """Fallback similarity search when pgvector RPC is not available"""
        import numpy as np

        client = self.get_supabase_client()

        # Get all vectors (limit to reasonable number for fallback)
        response = client.table('vectors').select('*').limit(1000).execute()

        if not response.data:
            return []

        # Compute cosine similarity for each vector
        similarities = []
        query_vec = np.array(query_embedding)

        for item in response.data:
            # 處理JSONB數據 - 可能是字符串或列表
            embedding_data = item['embedding']
            if isinstance(embedding_data, str):
                # 如果是字符串，嘗試解析JSON
                import json
                try:
                    embedding_data = json.loads(embedding_data)
                except:
                    logger.warning(f"無法解析向量字符串: {embedding_data[:50]}...")
                    continue

            db_embedding = np.array(embedding_data)
            # Cosine similarity
            similarity = np.dot(query_vec, db_embedding) / (np.linalg.norm(query_vec) * np.linalg.norm(db_embedding))

            similarities.append((similarity, item))

        # Sort by similarity (descending) and take top results
        similarities.sort(key=lambda x: x[0], reverse=True)
        top_results = similarities[:limit]

        results = []
        for similarity, item in top_results:
            # Convert UUID strings back to UUID objects
            item['vector_id'] = UUID(item['vector_id'])
            item['document_id'] = UUID(item['document_id'])
            if item.get('chunk_id'):
                item['chunk_id'] = UUID(item['chunk_id'])
            if item.get('fact_id'):
                item['fact_id'] = UUID(item['fact_id'])

            # Handle embedding - it might be stored as JSON string in Supabase
            if isinstance(item.get('embedding'), str):
                import json
                try:
                    item['embedding'] = json.loads(item['embedding'])
                except:
                    logger.warning(f"Failed to parse embedding JSON: {item['embedding'][:50]}...")
                    continue

            # Add similarity score to metadata
            item['similarity_score'] = float(similarity)

            vector_record = VectorRecord(**item)
            results.append(vector_record)

        logger.info(f"Fallback similarity search returned {len(results)} results")
        return results
