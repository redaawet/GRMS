#!/usr/bin/env python
import os
import sys

if os.name == "nt":
    os.environ["PATH"] = r"C:\OSGeo4W\bin;" + os.environ.get("PATH", "")
    os.environ["PROJ_LIB"] = os.environ.get("PROJ_LIB", r"C:\OSGeo4W\share\proj")
    os.environ["GDAL_DATA"] = os.environ.get("GDAL_DATA", r"C:\OSGeo4W\share\gdal")

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError("Django not installed") from exc
    execute_from_command_line(sys.argv)
