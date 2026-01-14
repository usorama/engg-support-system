/**
 * API Key Authentication Middleware
 *
 * Validates API key from Authorization header or x-api-key header.
 * In development mode (NODE_ENV !== 'production'), authentication can be skipped.
 */

import type { Request, Response, NextFunction } from "express";

export interface AuthConfig {
  /** Required API key for authentication */
  apiKey?: string;
  /** Skip auth if API key not configured (development only) */
  allowSkipInDev?: boolean;
  /** Paths to exclude from authentication */
  excludePaths?: string[];
}

/**
 * Creates API key authentication middleware
 */
export function createAuthMiddleware(config: AuthConfig = {}) {
  const {
    apiKey = process.env.ESS_API_KEY,
    allowSkipInDev = true,
    excludePaths = ["/health", "/"],
  } = config;

  return (req: Request, res: Response, next: NextFunction): void => {
    // Skip auth for excluded paths
    if (excludePaths.includes(req.path)) {
      next();
      return;
    }

    // In development, allow skipping auth if API key not configured
    const isDev = process.env.NODE_ENV !== "production";
    if (!apiKey && isDev && allowSkipInDev) {
      // Log warning but allow request
      if (req.path === "/query" || req.path.startsWith("/conversation")) {
        console.warn(
          `[AUTH] ESS_API_KEY not configured - auth skipped in development for ${req.path}`
        );
      }
      next();
      return;
    }

    // In production, API key is required
    if (!apiKey) {
      console.error("[AUTH] ESS_API_KEY not configured - rejecting request");
      res.status(503).json({
        error: "Service unavailable",
        message: "API authentication not configured",
      });
      return;
    }

    // Extract API key from request
    const authHeader = req.headers.authorization;
    const apiKeyHeader = req.headers["x-api-key"];

    let providedKey: string | undefined;

    // Check Authorization header (Bearer token)
    if (authHeader?.startsWith("Bearer ")) {
      providedKey = authHeader.slice(7);
    }
    // Check x-api-key header
    else if (typeof apiKeyHeader === "string") {
      providedKey = apiKeyHeader;
    }

    // Validate key
    if (!providedKey) {
      res.status(401).json({
        error: "Unauthorized",
        message: "Missing API key. Provide via Authorization: Bearer <key> or x-api-key header",
      });
      return;
    }

    // Constant-time comparison to prevent timing attacks
    if (!timingSafeEqual(providedKey, apiKey)) {
      res.status(403).json({
        error: "Forbidden",
        message: "Invalid API key",
      });
      return;
    }

    // Auth successful
    next();
  };
}

/**
 * Timing-safe string comparison to prevent timing attacks
 */
function timingSafeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) {
    return false;
  }

  let result = 0;
  for (let i = 0; i < a.length; i++) {
    result |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return result === 0;
}

/**
 * Default auth middleware instance
 */
export const authMiddleware = createAuthMiddleware();
