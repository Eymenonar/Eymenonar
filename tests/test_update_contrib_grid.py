import unittest

from scripts.update_contrib_grid import (
    filter_qualifying_repositories,
    render_grid,
    replace_generated_section,
)


class ContributionGridTests(unittest.TestCase):
    def test_filters_owned_low_star_and_duplicate_repositories(self):
        pull_requests = [
            {"repository_url": "https://api.github.com/repos/acme/big"},
            {"repository_url": "https://api.github.com/repos/acme/big"},
            {"repository_url": "https://api.github.com/repos/acme/small"},
            {"repository_url": "https://api.github.com/repos/Eymenonar/own"},
        ]
        repositories = {
            "acme/big": {"full_name": "acme/big", "html_url": "https://github.com/acme/big", "stargazers_count": 1500},
            "acme/small": {"full_name": "acme/small", "html_url": "https://github.com/acme/small", "stargazers_count": 999},
            "Eymenonar/own": {"full_name": "Eymenonar/own", "html_url": "https://github.com/Eymenonar/own", "stargazers_count": 5000},
        }

        result = filter_qualifying_repositories(pull_requests, repositories, "Eymenonar", 1000)

        self.assertEqual(["acme/big"], [repo["full_name"] for repo in result])

    def test_renders_seven_columns_and_pads_last_row(self):
        repositories = [
            {"full_name": f"org/repo-{index}", "html_url": f"https://github.com/org/repo-{index}", "stargazers_count": 1000 + index}
            for index in range(8)
        ]

        rendered = render_grid(repositories, columns=7)

        self.assertEqual(2, rendered.count("<tr>"))
        self.assertEqual(14, rendered.count("<td"))
        self.assertIn("org/repo-7", rendered)

    def test_renders_empty_state_when_no_repository_qualifies(self):
        rendered = render_grid([], columns=7)

        self.assertIn("1.000+", rendered)
        self.assertNotIn("<table", rendered)

    def test_replaces_only_generated_section(self):
        readme = "before\n<!-- CONTRIB-GRID:START -->\nold\n<!-- CONTRIB-GRID:END -->\nafter\n"

        updated = replace_generated_section(readme, "new")

        self.assertEqual(
            "before\n<!-- CONTRIB-GRID:START -->\nnew\n<!-- CONTRIB-GRID:END -->\nafter\n",
            updated,
        )

    def test_repository_contains_daily_workflow_and_readme_markers(self):
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        workflow = (root / ".github/workflows/update-contrib-grid.yml").read_text()
        readme = (root / "README.md").read_text()

        self.assertIn("cron: '15 0 * * *'", workflow)
        self.assertIn("contents: write", workflow)
        self.assertIn("MIN_STARS: '1000'", workflow)
        self.assertIn("<!-- CONTRIB-GRID:START -->", readme)
        self.assertIn("<!-- CONTRIB-GRID:END -->", readme)


if __name__ == "__main__":
    unittest.main()
