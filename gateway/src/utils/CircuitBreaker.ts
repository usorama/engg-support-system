/**
 * Circuit Breaker - Cascade Failure Prevention
 *
 * Implements the circuit breaker pattern to prevent cascade failures.
 * When a service fails repeatedly, the circuit "opens" and fails fast
 * instead of waiting for timeouts.
 *
 * States:
 * - CLOSED: Normal operation, requests pass through
 * - OPEN: Service is failing, requests fail immediately
 * - HALF_OPEN: Testing if service has recovered
 */

// ============================================================================
// Types
// ============================================================================

/**
 * Circuit breaker states
 */
export type CircuitState = "closed" | "open" | "half_open";

/**
 * Circuit breaker configuration
 */
export interface CircuitBreakerConfig {
  /** Number of failures before opening circuit */
  failureThreshold?: number | undefined;
  /** Time in ms before transitioning to half-open */
  resetTimeout?: number | undefined;
  /** Number of successes in half-open to close circuit */
  successThreshold?: number | undefined;
  /** Optional name for logging */
  name?: string | undefined;
  /** Callback when state changes */
  onStateChange?: ((from: CircuitState, to: CircuitState) => void) | undefined;
}

/**
 * Circuit breaker statistics
 */
export interface CircuitBreakerStats {
  /** Current state */
  state: CircuitState;
  /** Total failures since last close */
  failures: number;
  /** Total successes since last open */
  successes: number;
  /** Time of last failure */
  lastFailure?: Date | undefined;
  /** Time circuit was opened */
  openedAt?: Date | undefined;
  /** Total times circuit has opened */
  totalOpens: number;
  /** Total requests handled */
  totalRequests: number;
  /** Total requests rejected (circuit open) */
  totalRejected: number;
}

/**
 * Error thrown when circuit is open
 */
export class CircuitOpenError extends Error {
  constructor(
    public readonly circuitName: string,
    public readonly openedAt: Date,
    public readonly resetAt: Date
  ) {
    super(`Circuit breaker '${circuitName}' is open. Will reset at ${resetAt.toISOString()}`);
    this.name = "CircuitOpenError";
  }
}

// ============================================================================
// Circuit Breaker Implementation
// ============================================================================

/**
 * Circuit Breaker
 *
 * Wraps async operations with circuit breaker protection.
 */
export class CircuitBreaker {
  private state: CircuitState = "closed";
  private failures = 0;
  private successes = 0;
  private lastFailure: Date | undefined;
  private openedAt: Date | undefined;
  private totalOpens = 0;
  private totalRequests = 0;
  private totalRejected = 0;

  private readonly name: string;
  private readonly failureThreshold: number;
  private readonly resetTimeout: number;
  private readonly successThreshold: number;
  private readonly onStateChange: ((from: CircuitState, to: CircuitState) => void) | undefined;

  constructor(config: CircuitBreakerConfig = {}) {
    this.name = config.name ?? "default";
    this.failureThreshold = config.failureThreshold ?? 5;
    this.resetTimeout = config.resetTimeout ?? 30000; // 30 seconds
    this.successThreshold = config.successThreshold ?? 3;
    this.onStateChange = config.onStateChange;
  }

  /**
   * Execute a function through the circuit breaker
   */
  async execute<T>(fn: () => Promise<T>): Promise<T> {
    this.totalRequests++;

    // Check if circuit is open
    if (this.state === "open") {
      if (this.shouldAttemptReset()) {
        this.transitionTo("half_open");
      } else {
        this.totalRejected++;
        throw new CircuitOpenError(
          this.name,
          this.openedAt!,
          new Date(this.openedAt!.getTime() + this.resetTimeout)
        );
      }
    }

    try {
      const result = await fn();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  /**
   * Check if we should attempt reset (half-open)
   */
  private shouldAttemptReset(): boolean {
    if (!this.openedAt) return false;
    return Date.now() - this.openedAt.getTime() >= this.resetTimeout;
  }

  /**
   * Handle successful execution
   */
  private onSuccess(): void {
    this.failures = 0;
    this.lastFailure = undefined;

    if (this.state === "half_open") {
      this.successes++;
      if (this.successes >= this.successThreshold) {
        this.transitionTo("closed");
      }
    }
  }

  /**
   * Handle failed execution
   */
  private onFailure(): void {
    this.lastFailure = new Date();
    this.failures++;
    this.successes = 0;

    if (this.state === "half_open") {
      // Single failure in half-open reopens circuit
      this.transitionTo("open");
    } else if (this.state === "closed" && this.failures >= this.failureThreshold) {
      this.transitionTo("open");
    }
  }

  /**
   * Transition to a new state
   */
  private transitionTo(newState: CircuitState): void {
    if (this.state === newState) return;

    const oldState = this.state;
    this.state = newState;

    console.log(`[CircuitBreaker:${this.name}] ${oldState} -> ${newState}`);

    if (newState === "open") {
      this.openedAt = new Date();
      this.totalOpens++;
    } else if (newState === "closed") {
      this.failures = 0;
      this.successes = 0;
      this.openedAt = undefined;
    } else if (newState === "half_open") {
      this.successes = 0;
    }

    this.onStateChange?.(oldState, newState);
  }

  /**
   * Manually trip the circuit (open it)
   */
  trip(): void {
    this.transitionTo("open");
  }

  /**
   * Manually reset the circuit (close it)
   */
  reset(): void {
    this.transitionTo("closed");
  }

  /**
   * Get current state
   */
  getState(): CircuitState {
    // Auto-transition from open to half-open if timeout passed
    if (this.state === "open" && this.shouldAttemptReset()) {
      this.transitionTo("half_open");
    }
    return this.state;
  }

  /**
   * Get statistics
   */
  getStats(): CircuitBreakerStats {
    return {
      state: this.getState(),
      failures: this.failures,
      successes: this.successes,
      lastFailure: this.lastFailure,
      openedAt: this.openedAt,
      totalOpens: this.totalOpens,
      totalRequests: this.totalRequests,
      totalRejected: this.totalRejected,
    };
  }

  /**
   * Check if circuit allows requests
   */
  isAllowed(): boolean {
    const state = this.getState();
    return state === "closed" || state === "half_open";
  }

  /**
   * Get circuit name
   */
  getName(): string {
    return this.name;
  }
}

// ============================================================================
// Circuit Breaker Registry
// ============================================================================

/**
 * Registry for managing multiple circuit breakers
 */
export class CircuitBreakerRegistry {
  private breakers: Map<string, CircuitBreaker> = new Map();
  private defaultConfig: CircuitBreakerConfig;

  constructor(defaultConfig: CircuitBreakerConfig = {}) {
    this.defaultConfig = defaultConfig;
  }

  /**
   * Get or create a circuit breaker
   */
  get(name: string, config?: CircuitBreakerConfig): CircuitBreaker {
    let breaker = this.breakers.get(name);

    if (!breaker) {
      breaker = new CircuitBreaker({
        ...this.defaultConfig,
        ...config,
        name,
      });
      this.breakers.set(name, breaker);
    }

    return breaker;
  }

  /**
   * Check if a circuit breaker exists
   */
  has(name: string): boolean {
    return this.breakers.has(name);
  }

  /**
   * Get all circuit breaker stats
   */
  getAllStats(): Record<string, CircuitBreakerStats> {
    const stats: Record<string, CircuitBreakerStats> = {};
    for (const [name, breaker] of this.breakers) {
      stats[name] = breaker.getStats();
    }
    return stats;
  }

  /**
   * Reset all circuit breakers
   */
  resetAll(): void {
    for (const breaker of this.breakers.values()) {
      breaker.reset();
    }
  }

  /**
   * Get summary of all circuits
   */
  getSummary(): {
    total: number;
    open: number;
    closed: number;
    halfOpen: number;
  } {
    let open = 0;
    let closed = 0;
    let halfOpen = 0;

    for (const breaker of this.breakers.values()) {
      switch (breaker.getState()) {
        case "open":
          open++;
          break;
        case "closed":
          closed++;
          break;
        case "half_open":
          halfOpen++;
          break;
      }
    }

    return {
      total: this.breakers.size,
      open,
      closed,
      halfOpen,
    };
  }
}

// ============================================================================
// Factory and Helpers
// ============================================================================

/**
 * Default circuit breaker registry
 */
export const defaultRegistry = new CircuitBreakerRegistry({
  failureThreshold: 5,
  resetTimeout: 30000,
  successThreshold: 3,
});

/**
 * Wrap a function with circuit breaker protection
 */
export function withCircuitBreaker<T extends (...args: unknown[]) => Promise<unknown>>(
  fn: T,
  name: string,
  config?: CircuitBreakerConfig
): T {
  const breaker = defaultRegistry.get(name, config);

  return (async (...args: unknown[]) => {
    return breaker.execute(() => fn(...args));
  }) as T;
}

/**
 * Decorator for class methods (TypeScript experimental)
 */
export function circuitBreaker(name: string, config?: CircuitBreakerConfig) {
  return function (
    _target: unknown,
    _propertyKey: string,
    descriptor: PropertyDescriptor
  ) {
    const original = descriptor.value as (...args: unknown[]) => Promise<unknown>;
    const breaker = defaultRegistry.get(name, config);

    descriptor.value = async function (...args: unknown[]) {
      return breaker.execute(() => original.apply(this, args));
    };

    return descriptor;
  };
}

/**
 * Create circuit breakers for ESS services
 */
export function createESSCircuitBreakers(): CircuitBreakerRegistry {
  const registry = new CircuitBreakerRegistry({
    failureThreshold: 5,
    resetTimeout: 30000,
    successThreshold: 3,
    onStateChange: (from, to) => {
      if (to === "open") {
        console.error(`[CircuitBreaker] Circuit opened: ${from} -> ${to}`);
      } else if (to === "closed") {
        console.log(`[CircuitBreaker] Circuit recovered: ${from} -> ${to}`);
      }
    },
  });

  // Pre-create breakers for known services
  registry.get("neo4j", { failureThreshold: 5, resetTimeout: 30000 });
  registry.get("qdrant", { failureThreshold: 5, resetTimeout: 30000 });
  registry.get("redis", { failureThreshold: 3, resetTimeout: 15000 });
  registry.get("ollama", { failureThreshold: 5, resetTimeout: 60000 });
  registry.get("synthesis", { failureThreshold: 3, resetTimeout: 45000 });

  return registry;
}
