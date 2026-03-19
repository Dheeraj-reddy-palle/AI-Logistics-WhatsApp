"""
Tools module — minimal, no OpenAI function calling definitions needed.
All tool logic is now handled directly by the agent state machine.
"""

# Vehicle types available for booking
VEHICLE_TYPES = ["motorcycle", "car", "van", "truck"]

# Weight limits
MIN_WEIGHT_KG = 0.1
MAX_WEIGHT_KG = 50000
