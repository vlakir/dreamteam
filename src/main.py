"""Application entry point."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def main() -> None:
    """Run the application."""
    logging.basicConfig(level=logging.INFO)
    logger.info('Hello from dreamteam!')


if __name__ == '__main__':
    main()
