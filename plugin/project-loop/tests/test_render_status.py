import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
INIT = ROOT / "scripts/init_project_loop.py"
RENDER = ROOT / "scripts/render_status.py"


class RenderTests(unittest.TestCase):
    def test_render_is_deterministic_and_state_immutable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["python3", str(INIT), "--project-root", tmp, "--project-id", "sample-project"], check=True, capture_output=True)
            state = root / ".project-loop/state.json"
            before = state.read_bytes()
            first = subprocess.run(["python3", str(RENDER), "--project-root", tmp], text=True, capture_output=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            content = (root / "docs/project/STATUS.md").read_text()
            second = subprocess.run(["python3", str(RENDER), "--project-root", tmp], text=True, capture_output=True)
            self.assertEqual(second.returncode, 0)
            self.assertEqual(content, (root / "docs/project/STATUS.md").read_text())
            self.assertEqual(before, state.read_bytes())
            self.assertIn("`DRAFT`", content)


if __name__ == "__main__":
    unittest.main()
