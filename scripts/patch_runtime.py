#!/usr/bin/env python3
"""Make WPE runtime paths relative to libWPEWebKit's installed location."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]


def patch(source: Path) -> None:
    webkit = source / "Source/WebKit"
    changes = {
        "Shared/glib/ProcessExecutablePathGLib.cpp": (
            "FileSystem::stringFromFileSystemRepresentation(PKGLIBEXECDIR)",
            "FileSystem::stringFromFileSystemRepresentation(wpeRuntimeDirectory())",
        ),
        "UIProcess/API/glib/WebKitWebContext.cpp": (
            'static const char* injectedBundlePath = PKGLIBDIR G_DIR_SEPARATOR_S "injected-bundle" G_DIR_SEPARATOR_S;',
            'static const char* injectedBundlePath = g_build_filename(wpeRuntimeDirectory(), "injected-bundle", nullptr);',
        ),
        "UIProcess/Launcher/glib/BubblewrapLauncher.cpp": (
            '"--ro-bind-try", PKGLIBEXECDIR, PKGLIBEXECDIR,',
            '"--ro-bind-try", wpeRuntimeDirectory(), wpeRuntimeDirectory(),',
        ),
    }

    outputs: dict[Path, str] = {}
    for relative_path, (old, new) in changes.items():
        path = webkit / relative_path
        text = path.read_text()
        if text.count(old) != 1 or text.count('#include "config.h"') != 1:
            raise ValueError(f"Unexpected WPE source: {path}")
        outputs[path] = text.replace(old, new).replace(
            '#include "config.h"',
            '#include "config.h"\n#include "WPERuntimeDirectory.h"',
        )

    # Validate every source seam before changing any of them.
    for path, text in outputs.items():
        path.write_text(text)
    (webkit / "Shared/glib/WPERuntimeDirectory.h").write_bytes(
        (ROOT / "patches/WPERuntimeDirectory.h").read_bytes()
    )

    system_heap = source / "Source/bmalloc/bmalloc/SystemHeap.cpp"
    if system_heap.is_file():
        heap_text = system_heap.read_text()
        old_write = "m_sizeMap[result] = size;"
        new_write = "m_sizeMap.insert_or_assign(result, size);"
        old_read = "size = m_sizeMap[base];\n        size_t numErased = m_sizeMap.erase(base);"
        new_read = "auto it = m_sizeMap.find(base);\n        RELEASE_BASSERT(it != m_sizeMap.end());\n        size = it->second;\n        m_sizeMap.erase(it);"
        if old_write in heap_text and old_read in heap_text:
            heap_text = heap_text.replace(old_write, new_write, 1).replace(old_read, new_read, 1)
            system_heap.write_text(heap_text)


if __name__ == "__main__":
    patch(Path(sys.argv[1]))
