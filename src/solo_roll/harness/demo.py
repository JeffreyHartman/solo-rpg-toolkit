"""A small hand-made map for trying the harness before any generator exists."""

__all__ = ["DEMO_MAP", "DEMO_START", "DEMO_PARTY"]

DEMO_MAP = {
    "areas": {
        "gate": {"name": "Gatehouse", "x": 0, "y": 6, "w": 4, "h": 3},
        "hall": {"name": "Long Hall", "x": 6, "y": 6, "w": 8, "h": 3},
        "well": {"name": "Well Room", "x": 16, "y": 5, "w": 4, "h": 5},
        "crypt": {"name": "Crypt", "x": 8, "y": 0, "w": 4, "h": 4},
        "cells": {"name": "Cells", "x": 8, "y": 11, "w": 5, "h": 3},
    },
    "connections": [
        {"id": "gate-hall", "a": "gate", "b": "hall", "label": "east arch"},
        {"id": "hall-crypt", "a": "hall", "b": "crypt", "label": "north stair"},
        {"id": "hall-well", "a": "hall", "b": "well", "label": "east door"},
        {"id": "hall-cells", "a": "hall", "b": "cells", "label": "south passage"},
        {"id": "well-crypt", "a": "well", "b": "crypt", "label": "narrow crawl"},
    ],
}
DEMO_START = "gate"
DEMO_PARTY = [{"name": "Brannoc"}]
