"""Tests for new_high fetcher."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from ashare_data.fetchers.new_high import NewHighStock, _parse_html, _parse_percent, fetch_new_high_stocks


class TestParsePercent(unittest.TestCase):
    """Test percentage parsing."""

    def test_parse_valid_percent(self):
        self.assertEqual(_parse_percent("7.99%"), 7.99)
        self.assertEqual(_parse_percent("10.00%"), 10.0)

    def test_parse_empty_string(self):
        self.assertIsNone(_parse_percent(""))

    def test_parse_invalid_string(self):
        self.assertIsNone(_parse_percent("invalid"))


class TestParseHtml(unittest.TestCase):
    """Test HTML parsing."""

    def test_parse_valid_html(self):
        html = """
        <table>
            <tr><th>序号</th><th>代码</th><th>名称</th></tr>
            <tr><td>1</td><td>603929</td><td>亚翔集成</td><td>10.00%</td><td>1.85%</td><td>191.18</td><td>184.92</td><td>2026-03-20</td></tr>
            <tr><td>2</td><td>603115</td><td>海星股份</td><td>10.00%</td><td>4.14%</td><td>35.21</td><td>32.99</td><td>2026-03-18</td></tr>
        </table>
        """
        stocks = _parse_html(html)
        self.assertEqual(len(stocks), 2)
        self.assertEqual(stocks[0].code, "603929")
        self.assertEqual(stocks[0].name, "亚翔集成")
        self.assertEqual(stocks[0].change_pct, 10.0)

    def test_parse_empty_table(self):
        html = "<table><tr><th>Header</th></tr></table>"
        stocks = _parse_html(html)
        self.assertEqual(len(stocks), 0)

    def test_parse_no_table(self):
        html = "<div>No table here</div>"
        stocks = _parse_html(html)
        self.assertEqual(len(stocks), 0)


class TestFetchNewHighStocks(unittest.TestCase):
    """Test fetch_new_high_stocks function."""

    @patch("ashare_data.fetchers.new_high._fetch_html")
    def test_fetch_success(self, mock_fetch):
        mock_fetch.return_value = """
        <table>
            <tr><th>序号</th><th>代码</th><th>名称</th></tr>
            <tr><td>1</td><td>603929</td><td>亚翔集成</td><td>10.00%</td><td>1.85%</td><td>191.18</td><td>184.92</td><td>2026-03-20</td></tr>
        </table>
        """
        stocks = fetch_new_high_stocks()
        self.assertEqual(len(stocks), 1)
        self.assertIsInstance(stocks[0], NewHighStock)

    @patch("ashare_data.fetchers.new_high._fetch_html")
    def test_fetch_raises_on_error(self, mock_fetch):
        mock_fetch.side_effect = Exception("Network error")
        with self.assertRaises(RuntimeError):
            fetch_new_high_stocks()


if __name__ == "__main__":
    unittest.main()
