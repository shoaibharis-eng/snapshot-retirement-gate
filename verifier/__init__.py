"""A verifier that decides when a frozen test suite may be retired.

Three records feed one decision:

* ``verifier.log``      - append-only instruction log; every entry carries its scope
* ``verifier.snapshot`` - the project's shape and the suite's bytes at freeze time
* ``verifier.gate``     - weighs the log, the snapshot and observed behaviour

``verifier.suite`` runs the frozen suite and ``verifier.trace`` renders a decision.
"""
