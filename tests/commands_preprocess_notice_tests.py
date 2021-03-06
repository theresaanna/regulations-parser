from datetime import date
from unittest import TestCase

from click.testing import CliRunner
from mock import patch

from regparser.commands.preprocess_notice import preprocess_notice
from regparser.index import dependency, entry
from regparser.notice.xml import NoticeXML
from tests.http_mixin import HttpMixin
from tests.xml_builder import LXMLBuilder, XMLBuilderMixin


class CommandsPreprocessNoticeTests(HttpMixin, XMLBuilderMixin, TestCase):
    def example_xml(self, effdate_str="", source=None):
        """Returns a simple notice-like XML structure"""
        self.tree = LXMLBuilder()
        with self.tree.builder("ROOT") as root:
            root.CONTENT()
            root.P()
            with root.EFFDATE() as effdate:
                effdate.P(effdate_str)
        return NoticeXML(self.tree.render_xml(), source)

    def expect_common_json(self, **kwargs):
        """Expect an HTTP call and return a common json respond"""
        params = {'effective_on': '2008-08-08',
                  'publication_date': '2007-07-07',
                  'full_text_xml_url': 'some://url',
                  'volume': 45}
        params.update(kwargs)
        self.expect_json_http(params)

    @patch('regparser.commands.preprocess_notice.notice_xmls_for_url')
    def test_single_notice(self, notice_xmls_for_url):
        """Integration test, verifying that if a document number is associated
        with only a single XML file, a single, modified result is written"""
        cli = CliRunner()
        self.expect_common_json()
        notice_xmls_for_url.return_value = [self.example_xml()]
        with cli.isolated_filesystem():
            cli.invoke(preprocess_notice, ['1234-5678'])
            self.assertEqual(1, len(entry.Notice()))

            written = entry.Notice('1234-5678').read()
            self.assertEqual(written.effective, date(2008, 8, 8))

    @patch('regparser.commands.preprocess_notice.notice_xmls_for_url')
    def test_missing_effective_date(self, notice_xmls_for_url):
        """We should not explode if no effective date is present. Instead, we
        should parse the effective date from the XML"""
        cli = CliRunner()
        self.expect_common_json(effective_on=None)
        notice_xmls_for_url.return_value = [
            self.example_xml("Effective January 1, 2001")]
        with cli.isolated_filesystem():
            cli.invoke(preprocess_notice, ['1234-5678'])
            written = entry.Notice('1234-5678').read()
            self.assertEqual(written.effective, date(2001, 1, 1))

    @patch('regparser.commands.preprocess_notice.notice_xmls_for_url')
    def test_split_notice(self, notice_xmls_for_url):
        """Integration test, testing whether a notice which has been split
        (due to having multiple effective dates) is written as multiple
        files"""
        cli = CliRunner()
        self.expect_common_json()
        notice_xmls_for_url.return_value = [
            self.example_xml("Effective January 1, 2001"),
            self.example_xml("Effective February 2, 2002"),
            self.example_xml("Effective March 3, 2003")]
        with cli.isolated_filesystem():
            cli.invoke(preprocess_notice, ['1234-5678'])
            notice_path = entry.Notice()
            self.assertEqual(3, len(notice_path))

            jan = (notice_path / '1234-5678_20010101').read()
            feb = (notice_path / '1234-5678_20020202').read()
            mar = (notice_path / '1234-5678_20030303').read()

            self.assertEqual(jan.effective, date(2001, 1, 1))
            self.assertEqual(feb.effective, date(2002, 2, 2))
            self.assertEqual(mar.effective, date(2003, 3, 3))

    @patch('regparser.commands.preprocess_notice.notice_xmls_for_url')
    def test_dependencies(self, notice_xmls_for_url):
        """If the xml comes from a local source, we should expect a dependency
        be present. Otherwise, we should expect no dependency"""
        cli = CliRunner()
        self.expect_common_json()
        notice_xmls_for_url.return_value = [self.example_xml(source='./here')]
        with cli.isolated_filesystem():
            cli.invoke(preprocess_notice, ['1234-5678'])
            entry_str = str(entry.Notice() / '1234-5678')
            with dependency.Graph().dependency_db() as db:
                self.assertTrue(entry_str in db)

        notice_xmls_for_url.return_value[0].source = 'http://example.com'
        with cli.isolated_filesystem():
            cli.invoke(preprocess_notice, ['1234-5678'])
            entry_str = str(entry.Notice() / '1234-5678')
            with dependency.Graph().dependency_db() as db:
                self.assertFalse(entry_str in db)
