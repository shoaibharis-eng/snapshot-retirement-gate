"""The reproduction: a toy project, scripted repairs and replayable scenarios.

``project/`` is the baseline codebase with the suite that gets frozen. It is
never edited in place. Every replay copies it to a scratch directory, freezes
it there, and lets a scripted repair drift the copy.
"""
