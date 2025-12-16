// Neo4j Database Clear Script
// This script will completely clear all nodes and relationships from the Neo4j database

// First, detach and delete all nodes (this will also delete all relationships)
MATCH (n)
DETACH DELETE n;

// Verify the database is empty
MATCH (n)
RETURN count(n) as remaining_nodes;

// Check remaining relationships (should be 0)
MATCH ()-[r]->()
RETURN count(r) as remaining_relationships;

// Optional: Clear all indexes and constraints (uncomment if needed)
// CALL apoc.schema.assert({}, {}) YIELD label, key, keys, unique, action
// RETURN label, key, keys, unique, action;

// Optional: Clear schema statistics
// CALL db.clearQueryCaches();

// Final verification
MATCH (n)
OPTIONAL MATCH (n)-[r]-()
RETURN
  count(DISTINCT n) as nodes,
  count(DISTINCT r) as relationships,
  count(DISTINCT labels(n)) as node_types,
  count(DISTINCT type(r)) as relationship_types;
