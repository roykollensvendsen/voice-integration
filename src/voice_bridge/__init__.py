"""A voice control plane: spoken words in, agent work out, through one gateway.

The voice layer is deliberately thin. It carries intent and short spoken
replies; every transcript, every plan and every long context lives in the
Hermes gateway and is addressed by identifier. What that costs and why it is
worth it is `docs/specification.md`.
"""

from voice_bridge.contract import VOICE_TOOLS, Tool

__all__ = ["VOICE_TOOLS", "Tool"]
