## File hygiene (storage rules)

Your session directory is `$SLOPSWEEP_ROOT/sessions/$SLOPSWEEP_SESSION/`.

1. Scratch goes in `tmp/` only (TMPDIR points there). It is deleted automatically.
2. Deliverables go in `outputs/` only, and only when the user asked for a file. Reply inline otherwise.
3. Do not create summary, notes, report, changelog, or explanation files unless asked.
4. Overwrite, don't multiply: never create _v2, _final, _new, _backup, or copy variants.
5. Log every file you create outside tmp/ with:
   slopsweep manifest add <path> --purpose "<why>" --verdict keep|discard
   Mark discard on anything that turned out not to be needed.
6. Delete what you created and no longer need before finishing, especially large generated data, screenshots, and build artifacts.
7. If one file would exceed 50 MB or a task would create over 100 files, stop and ask first.
8. Never touch files outside your session directory. Never delete anything git-tracked.
