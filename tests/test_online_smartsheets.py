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


class OnlineSmartSheetsTests(unittest.TestCase):
    def test_get_fields_is_read_only(self):
        smartsheets = load_module("online.smartsheets")
        runner = FakeRunner({"fields": []})

        result = smartsheets.get_fields(docid="DOCID", sheet_id="SHEETID", runner=runner)

        self.assertEqual(result, {"fields": []})
        self.assertEqual(
            runner.calls,
            [(["doc", "smartsheet_get_fields"], {"docid": "DOCID", "sheet_id": "SHEETID"})],
        )

    def test_add_records_requires_confirmation_and_preserves_records(self):
        smartsheets = load_module("online.smartsheets")
        records = [{"values": {"标题": [{"type": "text", "text": "Task"}], "工时": 2}}]

        with self.assertRaises(PermissionError):
            smartsheets.add_records(docid="DOCID", sheet_id="SHEETID", records=records, runner=FakeRunner())

        runner = FakeRunner()
        smartsheets.add_records(
            docid="DOCID",
            sheet_id="SHEETID",
            records=records,
            confirmed=True,
            runner=runner,
        )
        self.assertEqual(
            runner.calls,
            [
                (
                    ["doc", "smartsheet_add_records"],
                    {"docid": "DOCID", "sheet_id": "SHEETID", "records": records},
                )
            ],
        )


if __name__ == "__main__":
    unittest.main()
