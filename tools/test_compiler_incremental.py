from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.compiler_incremental import CancellationToken, CompilerCancelled, IncrementalCompilerState


class IncrementalCompilerStateTest(unittest.TestCase):
    def _write(self, root: Path, name: str, text: str) -> Path:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_unchanged_inputs_reuse_same_snapshot_and_structural_load_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._write(root, "app.aidl", "module app\nentity Item {}\n")
            state = IncrementalCompilerState([root])
            first = state.snapshot_for(source)
            for _ in range(63):
                self.assertIs(first, state.snapshot_for(source))
            self.assertEqual(1, state.stats.builds)
            self.assertEqual(1, state.stats.misses)
            self.assertEqual(63, state.stats.hits)

    def test_unsaved_change_invalidates_entire_owning_root_transitively(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._write(root, "app.aidl", "module app\nimport lib.Item\nentity Uses { value: Item }\n")
            library = self._write(root, "lib.aidl", "module lib\nexport entity Item {}\n")
            state = IncrementalCompilerState([root])
            first = state.snapshot_for(source)
            assert first is not None
            offset = first.text(source).index("Item", first.text(source).index("value:"))
            self.assertEqual("resolved", first.resolve(source, offset).status)

            state.set_override(library, "module lib\nexport entity Renamed {}\n")
            second = state.snapshot_for(source)
            assert second is not None
            self.assertIsNot(first, second)
            self.assertEqual("unresolved", second.resolve(source, offset).status)
            self.assertGreaterEqual(state.stats.invalidations, 1)
            self.assertEqual(2, state.stats.builds)

    def test_saved_watcher_invalidation_observes_disk_change(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._write(root, "app.aidl", "module app\nentity Item {}\n")
            state = IncrementalCompilerState([root])
            first = state.snapshot_for(source)
            source.write_text("module app\nentity Item {}\nentity Item {}\n", encoding="utf-8")
            affected = state.invalidate_paths([source])
            second = state.snapshot_for(source)
            assert first is not None and second is not None
            self.assertEqual((root.resolve(),), affected)
            self.assertIsNot(first, second)
            self.assertTrue(any(item.code.value == "AIDL-R002" for item in second.diagnostics(source)))

    def test_roots_never_share_cache_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            left = base / "left"
            right = base / "right"
            left.mkdir()
            right.mkdir()
            left_source = self._write(left, "app.aidl", "module app\nentity Left {}\n")
            right_source = self._write(right, "app.aidl", "module app\nentity Right {}\n")
            state = IncrementalCompilerState([right, left])
            left_snapshot = state.snapshot_for(left_source)
            self.assertEqual(1, state.stats.builds)
            state.set_override(right_source, "module app\nentity Right {}\nentity Extra {}\n")
            self.assertIs(left_snapshot, state.snapshot_for(left_source))
            self.assertEqual(1, state.stats.builds)
            self.assertIsNotNone(state.snapshot_for(right_source))
            self.assertEqual(2, state.stats.builds)

    def test_cancelled_build_is_not_published_into_cache(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._write(root, "app.aidl", "module app\nentity Item {}\n")
            state = IncrementalCompilerState([root])
            token = CancellationToken()
            token.cancel()
            with self.assertRaises(CompilerCancelled):
                state.snapshot_for(source, token)
            self.assertEqual(0, state.stats.builds)
            self.assertEqual(0, state.stats.hits)
            self.assertIsNotNone(state.snapshot_for(source))
            self.assertEqual(1, state.stats.builds)


if __name__ == "__main__":
    unittest.main()
