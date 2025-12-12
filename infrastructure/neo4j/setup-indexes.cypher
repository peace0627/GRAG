// Neo4j Fulltext Indexes Setup for GraphRAG (Neo4j 5.x)
// This script creates the necessary fulltext indexes for entity and content search

// Create fulltext index for entity names
// This index enables fast text search on Entity node names
CREATE FULLTEXT INDEX entityNameIndex FOR (n:Entity) ON EACH [n.name, n.aliases];

// Create fulltext index for event descriptions
// This index enables temporal and event-based search
CREATE FULLTEXT INDEX eventIndex FOR (n:Event) ON EACH [n.description, n.type];

// Create fulltext index for visual fact descriptions
// This index enables search on visual content descriptions
CREATE FULLTEXT INDEX visualFactIndex FOR (n:VisualFact) ON EACH [n.description];

// Create fulltext index for chunk content
// This index enables direct text search on document chunks
CREATE FULLTEXT INDEX chunkContentIndex FOR (n:Chunk) ON EACH [n.text];

// Create fulltext index for document titles
// This index enables search on document metadata
CREATE FULLTEXT INDEX documentIndex FOR (n:Document) ON EACH [n.title, n.source_path];

// Verify indexes were created
SHOW INDEXES WHERE type = "FULLTEXT";
