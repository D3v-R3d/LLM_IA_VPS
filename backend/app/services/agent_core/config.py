"""
Agent Configuration

Loads configuration from environment variables.
Used by AgentOrchestrator.
"""

import os
from dataclasses import dataclass


@dataclass
class AgentConfig:
    """
    Configuration for AgentOrchestrator.
    Loaded from environment variables.
    """
    # Feature flag
    use_agent_orchestrator: bool = False

    # Execution limits
    max_steps: int = 3
    hard_limit: int = 6

    # Planning
    complexity_threshold: int = 3

    # Retry policy
    max_retry_per_step: int = 2
    max_retries_per_tool: int = 2

    # Context management
    context_max_messages: int = 10

    # Loop detection
    loop_window_size: int = 5
    max_consecutive_same_tool: int = 3

    # Logging
    debug: bool = False

    @classmethod
    def from_env(cls) -> "AgentConfig":
        """
        Load configuration from environment variables.
        """
        return cls(
            use_agent_orchestrator=os.getenv("USE_AGENT_ORCHESTRATOR", "false").lower() == "true",
            max_steps=int(os.getenv("AGENT_MAX_STEPS", "3")),
            hard_limit=int(os.getenv("AGENT_HARD_LIMIT", "6")),
            complexity_threshold=int(os.getenv("AGENT_COMPLEXITY_THRESHOLD", "3")),
            max_retry_per_step=int(os.getenv("AGENT_MAX_RETRY_PER_STEP", "2")),
            max_retries_per_tool=int(os.getenv("AGENT_MAX_RETRIES_PER_TOOL", "2")),
            context_max_messages=int(os.getenv("AGENT_CONTEXT_MAX_MESSAGES", "10")),
            loop_window_size=int(os.getenv("AGENT_LOOP_WINDOW_SIZE", "5")),
            max_consecutive_same_tool=int(os.getenv("AGENT_MAX_CONSECUTIVE_SAME_TOOL", "3")),
            debug=os.getenv("AGENT_DEBUG", "false").lower() == "true"
        )

    def validate(self) -> None:
        """
        Validate configuration values.
        """
        if self.max_steps > self.hard_limit:
            self.max_steps = self.hard_limit

        self.max_steps = max(1, self.max_steps)
        self.hard_limit = max(1, self.hard_limit)
        self.complexity_threshold = max(1, min(5, self.complexity_threshold))
        self.max_retry_per_step = max(0, self.max_retry_per_step)
        self.max_retries_per_tool = max(0, self.max_retries_per_tool)
        self.context_max_messages = max(3, self.context_max_messages)
        self.loop_window_size = max(3, self.loop_window_size)