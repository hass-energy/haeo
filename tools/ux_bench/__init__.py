"""Usability benchmark for HAEO's element config flows.

Each task seeds a live Home Assistant with real scenario inputs and a hub, then
a sandboxed Claude session plays a first-time user. It sees the browser only
through the ``browse`` command and works from a plain-English goal. The task
passes when the subentry data it leaves behind matches what the goal asks for.
"""
