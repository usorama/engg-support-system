#!/usr/bin/env node
/**
 * Generate PWA icons from SVG source
 *
 * Usage: node scripts/generate-icons.mjs
 *
 * Requires: npm install sharp
 */

import { readFileSync, writeFileSync, existsSync } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const publicDir = path.join(__dirname, '../public');

// Check if sharp is available
let sharp;
try {
  sharp = (await import('sharp')).default;
} catch {
  console.log('sharp not installed. Using SVG icons instead.');
  console.log('To generate PNG icons, run: npm install sharp');

  // Copy SVG as fallback
  const sizes = [
    { size: 180, name: 'apple-touch-icon.png' },
    { size: 192, name: 'pwa-192x192.png' },
    { size: 512, name: 'pwa-512x512.png' },
  ];

  console.log('\nSVG icons available:');
  for (const { name } of sizes) {
    const svgName = name.replace('.png', '.svg');
    const svgPath = path.join(publicDir, svgName);
    if (existsSync(svgPath)) {
      console.log(`  - ${svgName} (use as ${name})`);
    }
  }

  process.exit(0);
}

// Generate PNGs from SVGs
const icons = [
  { src: 'apple-touch-icon.svg', dest: 'apple-touch-icon.png', size: 180 },
  { src: 'pwa-192x192.svg', dest: 'pwa-192x192.png', size: 192 },
  { src: 'pwa-512x512.svg', dest: 'pwa-512x512.png', size: 512 },
];

async function generateIcons() {
  console.log('Generating PWA icons from SVG...\n');

  for (const { src, dest, size } of icons) {
    const svgPath = path.join(publicDir, src);
    const pngPath = path.join(publicDir, dest);

    if (!existsSync(svgPath)) {
      console.log(`  [SKIP] ${src} not found`);
      continue;
    }

    try {
      const svgContent = readFileSync(svgPath);

      await sharp(svgContent)
        .resize(size, size)
        .png()
        .toFile(pngPath);

      console.log(`  [OK] ${dest} (${size}x${size})`);
    } catch (error) {
      console.error(`  [ERROR] ${dest}: ${error.message}`);
    }
  }

  console.log('\nDone!');
}

generateIcons();
