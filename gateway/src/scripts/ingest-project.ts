#!/usr/bin/env npx tsx
/**
 * Project Ingestion Script
 *
 * Ingests a project's documents (markdown, code) into Qdrant for semantic search.
 *
 * Usage:
 *   source ../.env.prod && npx tsx src/scripts/ingest-project.ts --project paro --root /path/to/paro
 *
 * Features:
 * - Creates Qdrant collection if not exists
 * - Generates embeddings via Ollama
 * - Chunks large documents
 * - Stores with project metadata for multi-tenancy
 */

import { randomUUID } from "crypto";
import { readFileSync, readdirSync, statSync } from "fs";
import { join, extname, relative } from "path";

// ============================================================================
// Types
// ============================================================================

interface Document {
  id: string;
  content: string;
  filePath: string;
  project: string;
  nodeType: "CODE" | "MARKDOWN" | "DOCUMENT";
  embedding?: number[];
}

interface QdrantPoint {
  id: string;
  vector: number[];
  payload: {
    content: string;
    filePath: string;
    project: string;
    nodeType: string;
    createdAt: string;
  };
}

// ============================================================================
// Configuration
// ============================================================================

const CONFIG = {
  qdrant: {
    url: process.env.QDRANT_URL || "http://localhost:6333",
    collection: process.env.QDRANT_COLLECTION || "ess_knowledge_base",
  },
  ollama: {
    url: process.env.OLLAMA_URL || "http://localhost:11434",
    model: process.env.EMBEDDING_MODEL || "nomic-embed-text",
  },
  embedding: {
    dimensions: 768,
    batchSize: 10,
    timeout: 60000,
  },
  supported: {
    code: [".ts", ".tsx", ".js", ".jsx", ".py", ".go", ".rs", ".java"],
    docs: [".md", ".txt", ".json", ".yaml", ".yml"],
  },
  maxChunkSize: 4000, // characters per chunk
};

// ============================================================================
// Helpers
// ============================================================================

function inferNodeType(filePath: string): "CODE" | "MARKDOWN" | "DOCUMENT" {
  const ext = extname(filePath).toLowerCase();
  if (ext === ".md") return "MARKDOWN";
  if (CONFIG.supported.code.includes(ext)) return "CODE";
  return "DOCUMENT";
}

function chunkContent(content: string, maxSize: number): string[] {
  if (content.length <= maxSize) {
    return [content];
  }

  const chunks: string[] = [];
  const lines = content.split("\n");
  let currentChunk = "";

  for (const line of lines) {
    if (currentChunk.length + line.length + 1 > maxSize && currentChunk.length > 0) {
      chunks.push(currentChunk.trim());
      currentChunk = "";
    }
    currentChunk += line + "\n";
  }

  if (currentChunk.trim().length > 0) {
    chunks.push(currentChunk.trim());
  }

  return chunks;
}

// ============================================================================
// Qdrant Client
// ============================================================================

async function ensureCollection(): Promise<void> {
  console.log(`[Qdrant] Checking collection: ${CONFIG.qdrant.collection}`);

  // Check if collection exists
  const response = await fetch(
    `${CONFIG.qdrant.url}/collections/${CONFIG.qdrant.collection}`
  );

  if (response.ok) {
    console.log(`[Qdrant] Collection exists`);
    return;
  }

  // Create collection
  console.log(`[Qdrant] Creating collection with ${CONFIG.embedding.dimensions}-dim vectors`);

  const createResponse = await fetch(
    `${CONFIG.qdrant.url}/collections/${CONFIG.qdrant.collection}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        vectors: {
          size: CONFIG.embedding.dimensions,
          distance: "Cosine",
        },
      }),
    }
  );

  if (!createResponse.ok) {
    const error = await createResponse.text();
    throw new Error(`Failed to create collection: ${error}`);
  }

  console.log(`[Qdrant] Collection created`);
}

async function upsertPoints(points: QdrantPoint[]): Promise<void> {
  const response = await fetch(
    `${CONFIG.qdrant.url}/collections/${CONFIG.qdrant.collection}/points`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ points }),
    }
  );

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Failed to upsert points: ${error}`);
  }
}

async function getCollectionInfo(): Promise<{ pointsCount: number }> {
  const response = await fetch(
    `${CONFIG.qdrant.url}/collections/${CONFIG.qdrant.collection}`
  );

  if (!response.ok) {
    return { pointsCount: 0 };
  }

  const data = (await response.json()) as { result?: { points_count?: number } };
  return { pointsCount: data.result?.points_count ?? 0 };
}

// ============================================================================
// Ollama Embeddings
// ============================================================================

async function generateEmbedding(text: string): Promise<number[]> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), CONFIG.embedding.timeout);

  try {
    const response = await fetch(`${CONFIG.ollama.url}/api/embeddings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: CONFIG.ollama.model,
        prompt: text,
      }),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new Error(`Ollama embedding failed: ${response.status}`);
    }

    const data = (await response.json()) as { embedding?: number[] };

    if (!data.embedding) {
      throw new Error("No embedding in response");
    }

    return data.embedding;
  } catch (error) {
    clearTimeout(timeoutId);
    throw error;
  }
}

// ============================================================================
// File Discovery
// ============================================================================

function findFiles(
  dir: string,
  extensions: string[],
  files: string[] = []
): string[] {
  const items = readdirSync(dir);

  for (const item of items) {
    const fullPath = join(dir, item);

    // Skip common non-essential directories
    if (
      item === "node_modules" ||
      item === ".git" ||
      item === "dist" ||
      item === "__pycache__" ||
      item === "venv" ||
      item === ".next"
    ) {
      continue;
    }

    const stat = statSync(fullPath);

    if (stat.isDirectory()) {
      findFiles(fullPath, extensions, files);
    } else if (extensions.includes(extname(item).toLowerCase())) {
      files.push(fullPath);
    }
  }

  return files;
}

// ============================================================================
// Main Ingestion
// ============================================================================

async function ingestProject(
  projectName: string,
  rootDir: string
): Promise<void> {
  console.log(`\n╔═══════════════════════════════════════════════════════════════╗`);
  console.log(`║              ESS Project Ingestion                            ║`);
  console.log(`╚═══════════════════════════════════════════════════════════════╝\n`);

  console.log(`Project: ${projectName}`);
  console.log(`Root: ${rootDir}`);
  console.log(`Qdrant: ${CONFIG.qdrant.url}`);
  console.log(`Ollama: ${CONFIG.ollama.url}\n`);

  // 1. Ensure collection exists
  await ensureCollection();

  // 2. Find all supported files
  const allExtensions = [...CONFIG.supported.code, ...CONFIG.supported.docs];
  const files = findFiles(rootDir, allExtensions);
  console.log(`\nFound ${files.length} files to ingest\n`);

  if (files.length === 0) {
    console.log("No files found. Done.");
    return;
  }

  // 3. Process files
  let totalChunks = 0;
  let successCount = 0;
  let errorCount = 0;

  for (let i = 0; i < files.length; i++) {
    const filePath = files[i]!;
    const relativePath = relative(rootDir, filePath);
    const nodeType = inferNodeType(filePath);

    process.stdout.write(`[${i + 1}/${files.length}] ${relativePath}... `);

    try {
      const content = readFileSync(filePath, "utf-8");
      const chunks = chunkContent(content, CONFIG.maxChunkSize);

      const points: QdrantPoint[] = [];

      for (let chunkIdx = 0; chunkIdx < chunks.length; chunkIdx++) {
        const chunk = chunks[chunkIdx]!;
        const embedding = await generateEmbedding(chunk);

        points.push({
          id: randomUUID(),
          vector: embedding,
          payload: {
            content: chunk,
            filePath: relativePath,
            project: projectName,
            nodeType,
            createdAt: new Date().toISOString(),
          },
        });
      }

      await upsertPoints(points);

      totalChunks += chunks.length;
      successCount++;
      console.log(`✅ ${chunks.length} chunk(s)`);
    } catch (error) {
      errorCount++;
      console.log(`❌ ${error instanceof Error ? error.message : "Unknown error"}`);
    }
  }

  // 4. Summary
  const info = await getCollectionInfo();

  console.log(`\n═══════════════════════════════════════════════════════════════`);
  console.log(`SUMMARY`);
  console.log(`═══════════════════════════════════════════════════════════════\n`);
  console.log(`Files processed: ${successCount}/${files.length}`);
  console.log(`Chunks created: ${totalChunks}`);
  console.log(`Errors: ${errorCount}`);
  console.log(`Collection total: ${info.pointsCount} points`);
  console.log(`\n═══════════════════════════════════════════════════════════════\n`);
}

// ============================================================================
// CLI
// ============================================================================

async function main(): Promise<void> {
  const args = process.argv.slice(2);

  // Parse arguments
  let project = "";
  let root = "";

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === "--project" && args[i + 1]) {
      project = args[i + 1]!;
      i++;
    } else if (arg === "--root" && args[i + 1]) {
      root = args[i + 1]!;
      i++;
    }
  }

  if (!project || !root) {
    console.error("Usage: npx tsx src/scripts/ingest-project.ts --project NAME --root PATH");
    process.exit(1);
  }

  await ingestProject(project, root);
}

main().catch((err) => {
  console.error("Ingestion failed:", err);
  process.exit(1);
});
