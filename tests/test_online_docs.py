import importlib
import importlib.util
import unittest


def load_module(name):
    if importlib.util.find_spec(name) is None:
        raise AssertionError(f"{name} module should exist")
    return importlib.import_module(name)


class FakeRunner:
    def __init__(self, result=None):
        self.calls = []
        self.result = result if result is not None else {"errcode": 0}

    def __call__(self, args, payload=None):
        self.calls.append((list(args), payload))
        return self.result


class OnlineDocsTests(unittest.TestCase):
    def test_create_document_calls_wecom_cli_with_doc_type_3(self):
        docs = load_module("online.docs")
        runner = FakeRunner({"docid": "DOCID", "url": "https://doc"})

        result = docs.create_document("Project Notes", confirmed=True, runner=runner)

        self.assertEqual(result["docid"], "DOCID")
        self.assertEqual(
            runner.calls,
            [(["doc", "create_doc"], {"doc_name": "Project Notes", "doc_type": 3})],
        )

    def test_write_document_markdown_requires_confirmation(self):
        docs = load_module("online.docs")

        with self.assertRaises(PermissionError):
            docs.write_document_markdown(docid="DOCID", content="# Title", confirmed=False, runner=FakeRunner())

    def test_write_document_markdown_targets_docid_or_url(self):
        docs = load_module("online.docs")
        runner = FakeRunner()

        docs.write_document_markdown(docid="DOCID", content="# Title", confirmed=True, runner=runner)

        self.assertEqual(
            runner.calls,
            [
                (
                    ["doc", "edit_doc_content"],
                    {"docid": "DOCID", "content": "# Title", "content_type": 1},
                )
            ],
        )


if __name__ == "__main__":
    unittest.main()
