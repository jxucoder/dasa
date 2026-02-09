"""Tests for replay functionality."""

from dasa.cli.replay import _suggest_fix, _compare_outputs


class TestSuggestFix:
    def test_file_not_found(self):
        suggestion = _suggest_fix("FileNotFoundError", "file.csv", "pd.read_csv('file.csv')")
        assert suggestion is not None
        assert "path" in suggestion.lower()

    def test_module_not_found(self):
        suggestion = _suggest_fix("ModuleNotFoundError", "No module named 'sklearn'", "import sklearn")
        assert suggestion is not None
        assert "sklearn" in suggestion

    def test_name_error(self):
        suggestion = _suggest_fix("NameError", "name 'x' is not defined", "print(x)")
        assert suggestion is not None

    def test_no_suggestion(self):
        suggestion = _suggest_fix("RuntimeError", "something went wrong", "x = 1")
        assert suggestion is None

    def test_random_without_seed(self):
        suggestion = _suggest_fix("KeyError", "missing", "np.random.shuffle(data)")
        assert suggestion is not None
        assert "seed" in suggestion.lower()


class TestCompareOutputs:
    def test_empty_outputs_match(self):
        class MockResult:
            stdout = ""
            result = ""
        assert _compare_outputs([], MockResult()) is True

    def test_matching_stream(self):
        class MockResult:
            stdout = "hello world"
            result = ""
        saved = [{"output_type": "stream", "text": "hello world", "name": "stdout"}]
        assert _compare_outputs(saved, MockResult()) is True

    def test_different_output(self):
        class MockResult:
            stdout = "different"
            result = ""
        saved = [{"output_type": "stream", "text": "original", "name": "stdout"}]
        assert _compare_outputs(saved, MockResult()) is False
