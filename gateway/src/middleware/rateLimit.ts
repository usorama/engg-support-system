/**
 * Rate Limiting Middleware
 *
 * Prevents abuse by limiting requests per IP address.
 * Uses express-rate-limit with configurable windows and limits.
 */

import rateLimit from "express-rate-limit";
import type { Request, Response } from "express";

export interface RateLimitConfig {
  /** Time window in milliseconds (default: 60000 = 1 minute) */
  windowMs?: number;
  /** Max requests per window (default: 100) */
  maxRequests?: number;
  /** Message to return when rate limited */
  message?: string;
  /** Skip rate limiting in development */
  skipInDev?: boolean;
}

/**
 * Creates rate limiting middleware for query endpoints
 */
export function createQueryRateLimiter(config: RateLimitConfig = {}) {
  const {
    windowMs = parseInt(process.env.RATE_LIMIT_WINDOW_MS ?? "60000", 10),
    maxRequests = parseInt(process.env.RATE_LIMIT_MAX_REQUESTS ?? "100", 10),
    message = "Too many requests. Please wait before trying again.",
    skipInDev = false,
  } = config;

  // Skip in development if configured
  const isDev = process.env.NODE_ENV !== "production";
  if (isDev && skipInDev) {
    return (_req: Request, _res: Response, next: () => void) => next();
  }

  return rateLimit({
    windowMs,
    max: maxRequests,
    message: {
      error: "Rate limited",
      message,
      retryAfter: Math.ceil(windowMs / 1000),
    },
    standardHeaders: true, // Return rate limit info in headers
    legacyHeaders: false,
    keyGenerator: (req: Request): string => {
      // Use X-Forwarded-For if behind reverse proxy (Caddy)
      const forwarded = req.headers["x-forwarded-for"];
      if (typeof forwarded === "string") {
        const firstIp = forwarded.split(",")[0];
        return firstIp ? firstIp.trim() : "unknown";
      }
      return req.ip ?? "unknown";
    },
    handler: (req: Request, res: Response) => {
      console.warn(`[RATE_LIMIT] IP ${req.ip ?? "unknown"} exceeded rate limit`);
      res.status(429).json({
        error: "Rate limited",
        message,
        retryAfter: Math.ceil(windowMs / 1000),
      });
    },
  });
}

/**
 * Creates stricter rate limiting for conversation endpoints
 * (conversations are more resource-intensive)
 */
export function createConversationRateLimiter(config: RateLimitConfig = {}) {
  return createQueryRateLimiter({
    ...config,
    // Conversations are more expensive, limit to 50/min by default
    maxRequests: config.maxRequests ?? 50,
  });
}

/**
 * Default rate limiters
 */
export const queryRateLimiter = createQueryRateLimiter();
export const conversationRateLimiter = createConversationRateLimiter();
