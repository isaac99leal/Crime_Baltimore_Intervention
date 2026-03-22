#!/usr/bin/env python3
"""Somm Simulator - Entry Point.

A sommelier and beverage director simulation game for fine dining.
"""

import sys
from somm_simulator.engine.game import Game


def main():
    game = Game()
    game.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
