#!/usr/bin/env node
/**
 * Dynamic Claude Code Documentation Ingestion System
 *
 * Features:
 * - Dynamic content fetching from Claude Code docs
 * - Incremental updates (only processes changed docs)
 * - State tracking for resume capability
 * - Hash-based change detection
 * - Error handling and retry logic
 *
 * Usage:
 *   node scripts/ingest-sdk-docs.js              # Incremental update
 *   node scripts/ingest-sdk-docs.js --force       # Force re-ingest all
 *   node scripts/ingest-sdk-docs.js --dry-run     # Show what would change
 */

import { KnowledgeBase } from '../dist/core/KnowledgeBase.js';
import { readFileSync, writeFileSync, existsSync } from 'fs';
import { createHash } from 'crypto';

const STATE_FILE = './scripts/ingestion-state.json';
const REGISTRY_FILE = './scripts/claude-docs-registry.json';

// Parse command line args
const args = process.argv.slice(2);
const FORCE_ALL = args.includes('--force');
const DRY_RUN = args.includes('--dry-run');
const VERBOSE = args.includes('--verbose') || args.includes('-v');

// Configuration
const CONFIG = {
  qdrant: {
    url: process.env.QDRANT_URL || 'http://127.0.0.1:6333',
    collection: 'claude-code-docs',
    timeout: 120000,
    vectorSize: 768,
  },
  ollama: {
    vps: {
      url: process.env.OLLAMA_URL || 'http://127.0.0.1:11434',
      embedModel: 'nomic-embed-text',
      summarizeModel: 'llama3.2',
      timeout: 120000,
      maxRetries: 3,
    },
    local: { enabled: false },
  },
  openai: { enabled: false },
  localCache: { enabled: false },
  knowledgeGraph: { enabled: true },
  search: {
    semantic: { enabled: true, weight: 1.0, topK: 5, minScore: 0.5 },
    graph: { enabled: false },
  },
  summarization: { enabled: false },
  mcp: { enabled: false },
  logging: { level: VERBOSE ? 'info' : 'error', format: 'json' },
};

/**
 * Compute SHA-256 hash of content
 */
function computeHash(content) {
  return createHash('sha256').update(content).digest('hex');
}

/**
 * Load the docs registry
 */
function loadRegistry() {
  try {
    const content = readFileSync(REGISTRY_FILE, 'utf-8');
    return JSON.parse(content);
  } catch (error) {
    console.error(`Failed to load registry from ${REGISTRY_FILE}:`, error.message);
    process.exit(1);
  }
}

/**
 * Load ingestion state
 */
function loadState() {
  if (!existsSync(STATE_FILE)) {
    return {
      version: '1.0.0',
      lastIngestion: null,
      lastModifiedCheck: null,
      docs: {},
    };
  }
  try {
    const content = readFileSync(STATE_FILE, 'utf-8');
    return JSON.parse(content);
  } catch (error) {
    console.error(`Failed to load state from ${STATE_FILE}:`, error.message);
    return {
      version: '1.0.0',
      lastIngestion: null,
      lastModifiedCheck: null,
      docs: {},
    };
  }
}

/**
 * Save ingestion state
 */
function saveState(state) {
  try {
    writeFileSync(STATE_FILE, JSON.stringify(state, null, 2), 'utf-8');
  } catch (error) {
    console.error(`Failed to save state to ${STATE_FILE}:`, error.message);
  }
}

/**
 * Fetch content from URL
 */
async function fetchContent(url) {
  try {
    const response = await fetch(url, {
      headers: {
        'User-Agent': 'Claude-Code-Docs-Ingestor/1.0',
      },
      signal: AbortSignal.timeout(60000),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const html = await response.text();

    // Extract main content from Claude Code docs HTML structure
    // The docs use a specific HTML structure we need to parse
    const titleMatch = html.match(/<title>(.*?)<\/title>/i);
    const title = titleMatch ? titleMatch[1].replace(' | Claude Code', '') : 'Unknown';

    // Extract content from main content area
    const contentMatch = html.match(/<main[^>]*>([\s\S]*?)<\/main>/i);
    let content = contentMatch ? contentMatch[1] : html;

    // Clean up HTML - convert to markdown-like text
    content = content
      .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '')
      .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '')
      .replace(/<nav[^>]*>[\s\S]*?<\/nav>/gi, '')
      .replace(/<header[^>]*>[\s\S]*?<\/header>/gi, '')
      .replace(/<footer[^>]*>[\s\S]*?<\/footer>/gi, '')
      .replace(/<[^>]+>/g, match => {
        // Block elements become newlines
        if (/^<(?:div|p|br|h[1-6]|li|ul|ol|section|article)/i.test(match)) {
          return '\n\n';
        }
        // Inline elements removed
        return '';
      })
      .replace(/\n{3,}/g, '\n\n')
      .trim();

    return { title, content, url };
  } catch (error) {
    throw new Error(`Failed to fetch ${url}: ${error.message}`);
  }
}

/**
 * Check if doc needs re-ingestion
 */
function needsReingestion(doc, state, forceAll) {
  if (forceAll) return true;

  const docState = state.docs[doc.slug];
  if (!docState) return true;

  return docState.status !== 'success';
}

/**
 * Ingest a single document
 */
async function ingestDoc(doc, kb, state) {
  const slug = doc.slug;

  try {
    if (VERBOSE) console.log(`Fetching: ${doc.title} (${doc.url})`);

    // Fetch content
    const { title, content, url } = await fetchContent(doc.url);

    if (!content || content.length < 100) {
      throw new Error('Content too short or empty');
    }

    // Compute hash
    const hash = computeHash(content);

    // Check if changed
    const docState = state.docs[slug];
    if (docState && docState.hash === hash && !FORCE_ALL) {
      if (VERBOSE) console.log(`  ✓ Unchanged (skipping)`);
      state.docs[slug] = {
        ...docState,
        status: 'success',
        errorCount: 0,
        lastError: null,
      };
      return { skipped: true, slug };
    }

    if (DRY_RUN) {
      console.log(`  [DRY RUN] Would ingest: ${title}`);
      return { dryRun: true, slug, changed: true };
    }

    if (VERBOSE) console.log(`  Ingesting ${content.length} bytes...`);

    // Ingest to Knowledge Base
    await kb.ingest([
      {
        source: url,
        content: `# ${title}\n\n${content}`,
        metadata: {
          title,
          slug,
          category: doc.category,
          url,
          fetchedAt: new Date().toISOString(),
        },
      },
    ]);

    // Update state
    state.docs[slug] = {
      url: doc.url,
      lastProcessed: new Date().toISOString(),
      hash,
      status: 'success',
      errorCount: 0,
      lastError: null,
      remoteLastModified: new Date().toISOString(),
    };

    if (VERBOSE) console.log(`  ✓ Ingested successfully`);
    return { ingested: true, slug, changed: true };

  } catch (error) {
    const docState = state.docs[slug] || {};
    state.docs[slug] = {
      url: doc.url,
      lastProcessed: docState.lastProcessed || null,
      hash: docState.hash || null,
      status: 'error',
      errorCount: (docState.errorCount || 0) + 1,
      lastError: error.message,
      remoteLastModified: docState.remoteLastModified || null,
    };

    console.error(`  ✗ Error: ${error.message}`);
    return { error: true, slug, message: error.message };
  }
}

/**
 * Main ingestion flow
 */
async function main() {
  console.log('='.repeat(60));
  console.log('Claude Code Documentation Ingestion');
  console.log('='.repeat(60));

  if (DRY_RUN) {
    console.log('[DRY RUN MODE - No changes will be made]');
  }
  if (FORCE_ALL) {
    console.log('[FORCE MODE - Re-ingesting all documents]');
  }
  console.log('');

  // Load registry and state
  const registry = loadRegistry();
  const state = loadState();

  console.log(`Registry version: ${registry.version}`);
  console.log(`Total docs in registry: ${registry.docs.length}`);
  console.log(`State version: ${state.version}`);
  console.log(`Last ingestion: ${state.lastIngestion || 'Never'}`);
  console.log('');

  // Sort docs by priority
  const sortedDocs = [...registry.docs].sort((a, b) => a.priority - b.priority);

  // Determine which docs need processing
  const docsToProcess = sortedDocs.filter(doc => needsReingestion(doc, state, FORCE_ALL));

  console.log(`Docs to process: ${docsToProcess.length} / ${sortedDocs.length}`);
  console.log('');

  if (docsToProcess.length === 0) {
    console.log('✓ All documents are up to date!');
    return;
  }

  if (DRY_RUN) {
    console.log('Would process the following documents:\n');
    for (const doc of docsToProcess) {
      console.log(`  - ${doc.title} (${doc.url})`);
    }
    return;
  }

  // Initialize Knowledge Base
  let kb;
  try {
    kb = new KnowledgeBase(CONFIG);
    await kb.initialize();
    console.log('✓ Knowledge Base initialized');
    console.log('');
  } catch (error) {
    console.error('Failed to initialize Knowledge Base:', error.message);
    process.exit(1);
  }

  // Process docs
  const results = {
    total: docsToProcess.length,
    ingested: 0,
    skipped: 0,
    errors: 0,
    changed: 0,
  };

  for (const doc of docsToProcess) {
    const result = await ingestDoc(doc, kb, state);

    if (result.skipped) results.skipped++;
    else if (result.dryRun) continue;
    else if (result.error) results.errors++;
    else {
      results.ingested++;
      if (result.changed) results.changed++;
    }

    // Save state after each doc (for resilience)
    saveState(state);
  }

  // Update final state
  state.lastIngestion = new Date().toISOString();
  saveState(state);

  // Summary
  console.log('');
  console.log('='.repeat(60));
  console.log('Ingestion Summary');
  console.log('='.repeat(60));
  console.log(`Total docs processed: ${results.total}`);
  console.log(`Successfully ingested: ${results.ingested}`);
  console.log(`Skipped (unchanged): ${results.skipped}`);
  console.log(`Errors: ${results.errors}`);
  console.log(`Changed documents: ${results.changed}`);
  console.log('');

  // Get KB stats
  try {
    const stats = await kb.getStats();
    console.log('Knowledge Base Stats:');
    console.log(`  Total nodes: ${stats.totalNodes}`);
    console.log(`  Total relationships: ${stats.totalRelationships}`);
  } catch (error) {
    if (VERBOSE) console.error('Failed to get stats:', error.message);
  }

  console.log('');
  console.log('✓ Ingestion complete!');

  // Exit with error code if there were failures
  process.exit(results.errors > 0 ? 1 : 0);
}

// Run
main().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});
