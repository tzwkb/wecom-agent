import importlib
import importlib.util
import subprocess
import unittest


def load_module(name):
    if importlib.util.find_spec(name) is None:
        raise AssertionError(f"{name} module should exist")
    return importlib.import_module(name)


class OnlineWecomCliTests(unittest.TestCase):
    def test_run_json_passes_payload_as_json_argument(self):
        wecom_cli = load_module("online.wecom_cli")
        calls = []

        def fake_run(argv, capture_output, text, timeout, check):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 0, stdout='{"errcode":0}', stderr="")

        result = wecom_cli.run_json(
            ["doc", "create_doc"],
            {"doc_name": "Demo", "doc_type": 3},
            run=fake_run,
        )

        self.assertEqual(result, {"errcode": 0})
        self.assertEqual(calls[0][:4], ["wecom-cli", "doc", "create_doc", "--json"])
        self.assertIn('"doc_type":3', calls[0][4])

    def test_run_json_raises_structured_error_on_cli_failure(self):
        wecom_cli = load_module("online.wecom_cli")

        def fake_run(argv, capture_output, text, timeout, check):
            return subprocess.CompletedProcess(argv, 2, stdout="", stderr="unsupported")

        with self.assertRaises(wecom_cli.WecomCliError) as ctx:
            wecom_cli.run_json(["doc", "missing"], run=fake_run)

        self.assertEqual(ctx.exception.returncode, 2)
        self.assertIn("unsupported", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
