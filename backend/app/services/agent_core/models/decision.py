from enum import Enum


class Decision(Enum):
    """
    Pure output from evaluate_step - no side effects.
    Retry is handled inside _execute_with_retry(), not here.
    """
    CONTINUE = "continue"
    STOP = "stop"