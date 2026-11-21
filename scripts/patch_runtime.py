#!/usr/bin/env python3
"""Make WPE runtime paths relative to libWPEWebKit's installed location."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]

RELOCATION_CHANGES = {
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

DAMAGE_RELATIVE_PATH = "WebProcess/WebPage/CoordinatedGraphics/AcceleratedSurface.cpp"
DAMAGE_OLD = (
    "void AcceleratedSurface::didRenderFrame(TargetContents targetContents)\n"
    "{\n"
    "#if PLATFORM(GTK) || PLATFORM(WPE)\n"
)
DAMAGE_NEW = (
    "void AcceleratedSurface::didRenderFrame(TargetContents targetContents)\n"
    "{\n"
    "#if USE(WPE_RENDERER)\n"
    "    // The legacy WPE backend rotates physical dma-bufs behind one logical target.\n"
    "    if (m_swapChain.type() == SwapChain::Type::WPEBackend)\n"
    "        targetContents = TargetContents::Invalid;\n"
    "#endif\n"
    "#if PLATFORM(GTK) || PLATFORM(WPE)\n"
)


def patch(source: Path) -> None:
    webkit = source / "Source/WebKit"
    outputs: dict[Path, str] = {}

    def stage(relative_path: str, old: str, new: str, *, runtime_include: bool = False) -> None:
        path = webkit / relative_path
        text = path.read_text()
        if text.count(old) != 1:
            raise ValueError(f"Unexpected WPE source: {path}")
        if runtime_include:
            if text.count('#include "config.h"') != 1:
                raise ValueError(f"Unexpected WPE source: {path}")
            text = text.replace(
                '#include "config.h"',
                '#include "config.h"\n#include "WPERuntimeDirectory.h"',
            )
        outputs[path] = text.replace(old, new)

    for relative_path, (old, new) in RELOCATION_CHANGES.items():
        stage(relative_path, old, new, runtime_include=True)
    stage(DAMAGE_RELATIVE_PATH, DAMAGE_OLD, DAMAGE_NEW)

    # Validate every source seam before changing any of them.
    for path, text in outputs.items():
        path.write_text(text)
    (webkit / "Shared/glib/WPERuntimeDirectory.h").write_bytes(
        (ROOT / "patches/WPERuntimeDirectory.h").read_bytes()
    )


if __name__ == "__main__":
    patch(Path(sys.argv[1]))
