#!/usr/bin/env python3
"""
Sync embeddings from Neo4j to Qdrant.
Reads all nodes with embeddings from Neo4j and creates a Qdrant collection.
"""
import os
import sys
import json
import uuid
from typing import List, Dict, Any

# Install deps if needed
try:
    from neo4j import GraphDatabase
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "neo4j", "qdrant-client"])
    from neo4j import GraphDatabase
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct


def main():
    # Configuration from environment
    NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7688")
    NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "testpassword")
    QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6335")
    PROJECT_NAME = os.environ.get("PROJECT_NAME", "rad-engineer-v2")
    COLLECTION_NAME = f"ess_{PROJECT_NAME.replace('-', '_')}"
    VECTOR_SIZE = 768  # nomic-embed-text dimension

    print(f"Syncing project '{PROJECT_NAME}' from Neo4j to Qdrant...")
    print(f"Neo4j: {NEO4J_URI}")
    print(f"Qdrant: {QDRANT_URL}")
    print(f"Collection: {COLLECTION_NAME}")

    # Connect to Neo4j
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    # Connect to Qdrant
    qdrant = QdrantClient(url=QDRANT_URL)

    # Create collection if not exists
    collections = [c.name for c in qdrant.get_collections().collections]
    if COLLECTION_NAME not in collections:
        print(f"Creating collection '{COLLECTION_NAME}'...")
        qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)
        )
    else:
        print(f"Collection '{COLLECTION_NAME}' exists, will upsert points...")

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
                print(f"  Skipping {uid}: invalid embedding size {len(embedding) if embedding else 0}")
                continue

            # Create payload with metadata
            payload = {
                "uid": uid,
                "name": record["name"] or "",
                "qualified_name": record["qualified_name"] or "",
                "docstring": record["docstring"] or "",
                "path": record["path"] or record["file_path"] or "",
                "labels": record["labels"] or [],
                "project": PROJECT_NAME
            }

            # Generate a UUID from uid for Qdrant
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, uid))
            
            points.append(PointStruct(
                id=point_id,
                vector=embedding,
                payload=payload
            ))

    print(f"Found {len(points)} nodes with valid embeddings")

    if points:
        # Upsert in batches of 100
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i:i+batch_size]
            qdrant.upsert(collection_name=COLLECTION_NAME, points=batch)
            print(f"  Upserted batch {i//batch_size + 1}: {len(batch)} points")

        # Verify
        info = qdrant.get_collection(COLLECTION_NAME)
        print(f"\n✅ Sync complete!")
        print(f"   Collection: {COLLECTION_NAME}")
        print(f"   Points: {info.points_count}")
        print(f"   Vectors: {info.vectors_count}")
    else:
        print("❌ No valid embeddings found to sync!")

    driver.close()


if __name__ == "__main__":
    main()
