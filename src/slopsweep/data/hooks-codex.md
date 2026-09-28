# Codex / generic shell integration

Add to your session wrapper (slopsweep does not edit agent configs):

```bash
eval "$(slopsweep session new)"
# ... agent work ...
slopsweep session end
slopsweep run --apply
```

Export `SLOPSWEEP_ROOT` before `session new` if not using the default `~/agent-work`.
