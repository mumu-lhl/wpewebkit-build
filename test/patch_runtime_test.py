import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "patch_runtime", ROOT / "scripts/patch_runtime.py"
)
PATCH_RUNTIME = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(PATCH_RUNTIME)


class PatchRuntimeTest(unittest.TestCase):
    def test_all_patches_apply_and_patch_fails_closed(self):
        snippets = {
            "Shared/glib/ProcessExecutablePathGLib.cpp":
                "FileSystem::stringFromFileSystemRepresentation(PKGLIBEXECDIR)",
            "UIProcess/API/glib/WebKitWebContext.cpp":
                'static const char* injectedBundlePath = PKGLIBDIR G_DIR_SEPARATOR_S "injected-bundle" G_DIR_SEPARATOR_S;',
            "UIProcess/Launcher/glib/BubblewrapLauncher.cpp":
                '"--ro-bind-try", PKGLIBEXECDIR, PKGLIBEXECDIR,',
        }
        with tempfile.TemporaryDirectory() as temporary_directory:
            source = Path(temporary_directory)
            for relative_path, snippet in snippets.items():
                path = source / "Source/WebKit" / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('#include "config.h"\n' + snippet)
            damage_path = source / "Source/WebKit" / PATCH_RUNTIME.DAMAGE_RELATIVE_PATH
            damage_path.parent.mkdir(parents=True, exist_ok=True)
            damage_path.write_text(PATCH_RUNTIME.DAMAGE_OLD + "    TraceScope traceScope;\n")

            PATCH_RUNTIME.patch(source)

            for relative_path in snippets:
                text = (source / "Source/WebKit" / relative_path).read_text()
                self.assertIn("wpeRuntimeDirectory()", text)
                self.assertIn('#include "WPERuntimeDirectory.h"', text)
                self.assertNotIn("PKGLIBEXECDIR", text)
                self.assertNotIn("PKGLIBDIR", text)
            self.assertTrue(
                (source / "Source/WebKit/Shared/glib/WPERuntimeDirectory.h").is_file()
            )

            damage_text = damage_path.read_text()
            self.assertIn("targetContents = TargetContents::Invalid;", damage_text)
            self.assertIn("#if USE(WPE_RENDERER)", damage_text)
            self.assertNotIn(PATCH_RUNTIME.DAMAGE_OLD, damage_text)
            self.assertNotIn('#include "WPERuntimeDirectory.h"', damage_text)

            with self.assertRaises(ValueError):
                PATCH_RUNTIME.patch(source)


if __name__ == "__main__":
    unittest.main()
