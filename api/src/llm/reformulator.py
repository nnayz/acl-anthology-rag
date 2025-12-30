"""
LLM-based query reformulation.

This module uses an LLM to expand user queries into multiple
semantically meaningful search queries. This improves recall
by capturing different facets of the user's information need.

The reformulator is the core component that enables the system
to never embed raw user queries directly.
"""

