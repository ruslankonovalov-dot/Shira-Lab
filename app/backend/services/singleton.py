"""Singleton pattern decorator for service classes.

Usage:
    from app.backend.services.singleton import singleton

    @singleton
    class MyService:
        ...
"""
import threading
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar('T')


def singleton(cls: type[T]) -> Callable[..., T]:
    """Decorator that makes a class singleton (only one instance).

    Thread-safe: uses a lock to prevent race conditions during first instantiation.
    """
    instances: dict[type, T] = {}
    lock = threading.Lock()

    def get_instance(*args: Any, **kwargs: Any) -> T:
        if cls not in instances:
            with lock:
                if cls not in instances:
                    instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    def reset_instance() -> None:
        """Reset the singleton instance (useful for testing)."""
        with lock:
            if cls in instances:
                del instances[cls]

    # Preserve original class attributes
    get_instance.__name__ = cls.__name__
    get_instance.__doc__ = cls.__doc__
    setattr(get_instance, '_original_class', cls)
    setattr(get_instance, 'reset_instance', reset_instance)

    # Allow access to class methods
    setattr(get_instance, 'cls', cls)

    return get_instance
