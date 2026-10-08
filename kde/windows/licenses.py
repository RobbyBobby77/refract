"""Keep bundled dependency license files beside the portable executable."""
import importlib.metadata
from pathlib import Path
import shutil
import sys

destination = Path(sys.argv[1]) / "licenses"
destination.mkdir(parents=True, exist_ok=True)
for name in ("PySide6", "PySide6-Essentials", "PySide6-Addons", "shiboken6", "psutil", "pyinstaller"):
    distribution = importlib.metadata.distribution(name)
    for entry in distribution.files or ():
        if any(part.casefold() in ("licenses", "license", "copying") for part in entry.parts) or entry.name.casefold().startswith(("license", "copying", "notice")):
            source = Path(distribution.locate_file(entry))
            if source.is_file():
                target = destination / name / Path(*[p for p in entry.parts if p not in ("..", ".")])
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
