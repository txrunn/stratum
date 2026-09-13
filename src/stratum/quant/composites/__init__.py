"""Versioned macro composites, pure functions over the store.

Each composite bakes its formula (component series, weights, signs, window)
into a version string. Changing any of those is a new version — old runs
stay reproducible, exactly like semantic label versioning in ARCHITECTURE.md.
"""
