import pytest
from app.web.helpers import nl2br

class TestNl2br:
    def test_nl2br_none(self):
        assert nl2br(None) == ''

    def test_nl2br_empty(self):
        assert nl2br('') == ''

    def test_nl2br_single_line(self):
        assert nl2br('hello world') == 'hello world'

    def test_nl2br_newlines(self):
        assert nl2br('line1\nline2') == 'line1<br>\nline2'
        assert nl2br('a\nb\nc') == 'a<br>\nb<br>\nc'

    def test_nl2br_trailing_newline(self):
        assert nl2br('foo\n') == 'foo<br>\n'
