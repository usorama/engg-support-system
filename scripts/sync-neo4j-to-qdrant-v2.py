#!/usr/bin/env python3
"""
Sync embeddings from Neo4j to Qdrant v2 - with timeout fixes.
"""
import os
import sys
import uuid

from neo4j import GraphDatabase
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct


def main():
    NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7688")
    NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "testpassword")
    QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6335")
    PROJECT_NAME = os.environ.get("PROJECT_NAME", "rad-engineer-v2")
    COLLECTION_NAME = f"ess_{PROJECT_NAME.replace('-', '_')}"
    VECTOR_SIZE = 768

    print(f"Syncing project '{PROJECT_NAME}' from Neo4j to Qdrant...")

    # Connect to Neo4j
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    # Connect to Qdrant with extended timeout and skip version check
    qdrant = QdrantClient(
        url=QDRANT_URL,
        timeout=300,  # 5 minute timeout
        check_compatibility=False
    )

    # Create collection - wrap in try/catch
    try:
        collections = [c.name for c in qdrant.get_collections().collections]
        if COLLECTION_NAME not in collections:
            print(f"Creating collection '{COLLECTION_NAME}'...")
            qdrant.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
                timeout=60
            )
        else:
            print(f"Collection '{COLLECTION_NAME}' exists")
    except Exception as e:
        print(f"Collection check/create error: {e}")
        # Try to continue anyway

    # Query Neo4j for all nodes with embeddings
    query = """
    MATCH (n)
    WHERE n.project = $project AND n.embedding IS NOT NULL AND size(n.embedding) > 0
    RETURN 
        n.uid as uid,
        n.name as name,
        n.qualified_name as qualified_name,
        n.docstring as docstring,
        n.path as path,
        n.file_path as file_path,
        labels(n) as labels,
        n.embedding as embedding
    """

    points = []
    with driver.session() as session:
        result = session.run(query, project=PROJECT_NAME)
        for record in result:
            uid = record["uid"]
            embedding = record["embedding"]
            
            if not embedding or len(embedding) != VECTOR_SIZE:
                continue

            payload = {
                "uid": uid,
                "name": record["name"] or "",
                "qualified_name": record["qualified_name"] or "",
                "docstring": (record["docstring"] or "")[:500],  # Truncate long docstrings
                "path": record["path"] or record["file_path"] or "",
                "labels": record["labels"] or [],
                "project": PROJECT_NAME
            }

            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, uid))
            points.append(PointStruct(id=point_id, vector=embedding, payload=payload))

    print(f"Found {len(points)} nodes with valid embeddings")
    driver.close()

    if not points:
        print("❌ No valid embeddings found!")
        return

    # Upsert in small batches
    batch_size = 50
    for i in range(0, len(points), batch_size):
        batch = points[i:i+batch_size]
        try:
            qdrant.upsert(collection_name=COLLECTION_NAME, points=batch, wait=True)
            print(f"  ✓ Batch {i//batch_size + 1}: {len(batch)} points")
        except Exception as e:
            print(f"  ✗ Batch {i//batch_size + 1} failed: {e}")

    # Verify
    try:
        info = qdrant.get_collection(COLLECTION_NAME)
        print(f"\n✅ Sync complete! Collection has {info.points_count} points")
    except Exception as e:
        print(f"\n⚠️ Could not verify: {e}")


if __name__ == "__main__":
    main()
