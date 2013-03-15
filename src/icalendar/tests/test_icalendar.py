# coding: utf-8
import unittest
import doctest
import os
from icalendar import (
    cal,
    caselessdict,
    parser,
    prop,
)

OPTIONFLAGS = doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS


class IcalendarTestCase (unittest.TestCase):

    def test_long_lines(self):
        from icalendar.parser import Contentlines, Contentline
        c = Contentlines([Contentline('BEGIN:VEVENT\r\n')])
        c.append(Contentline(''.join('123456789 ' * 10) + '\r\n'))
        self.assertEqual(
            c.to_ical(),
            'BEGIN:VEVENT\r\n\r\n123456789 123456789 123456789 123456789 '
            '123456789 123456789 123456789 1234\r\n 56789 123456789 '
            '123456789 \r\n\r\n'
        )

        # from doctests
        # Notice that there is an extra empty string in the end of the content lines.
        # That is so they can be easily joined with: '\r\n'.join(contentlines)).
        self.assertEqual(Contentlines.from_ical('A short line\r\n'),
                         ['A short line', ''])
        self.assertEqual(Contentlines.from_ical('A faked\r\n  long line\r\n'),
                         ['A faked long line', ''])
        self.assertEqual(
            Contentlines.from_ical('A faked\r\n  long line\r\nAnd another '
                                   'lin\r\n\te that is folded\r\n'),
            ['A faked long line', 'And another line that is folded', '']
        )

    def test_contentline_class(self):
        from icalendar.parser import Contentline, Parameters
        from icalendar.prop import vText

        self.assertEqual(
            Contentline('Si meliora dies, ut vina, poemata reddit').to_ical(),
            'Si meliora dies, ut vina, poemata reddit'
        )

        # A long line gets folded
        c = Contentline(''.join(['123456789 '] * 10)).to_ical()
        self.assertEqual(
            c,
            ('123456789 123456789 123456789 123456789 123456789 123456789 '
             '123456789 1234\r\n 56789 123456789 123456789')
        )

        # A folded line gets unfolded
        self.assertEqual(
            Contentline.from_ical(c),
            ('123456789 123456789 123456789 123456789 123456789 123456789 '
             '123456789 123456789 123456789 123456789')
        )

        # Newlines in a string get need to be preserved
        self.assertEqual(
            Contentline('1234\n\n1234').to_ical(),
            '1234\r\n \r\n 1234'
        )

        # We do not fold within a UTF-8 character
        c = Contentline('This line has a UTF-8 character where it should be '
                        'folded. Make sure it g\xc3\xabts folded before that '
                        'character.')
        self.assertIn('\xc3\xab', c.to_ical())

        # Another test of the above
        c = Contentline('x' * 73 + '\xc3\xab' + '\\n ' + 'y' * 10)
        self.assertEqual(c.to_ical().count('\xc3'), 1)

        # Don't fail if we fold a line that is exactly X times 74 characters long:
        c = Contentline(''.join(['x'] * 148)).to_ical()

        # It can parse itself into parts. Which is a tuple of (name, params, vals)
        self.assertEqual(
            Contentline('dtstart:20050101T120000').parts(),
            ('dtstart', Parameters({}), '20050101T120000')
        )

        self.assertEqual(
            Contentline('dtstart;value=datetime:20050101T120000').parts(),
            ('dtstart', Parameters({'VALUE': 'datetime'}), '20050101T120000')
        )

        c = Contentline('ATTENDEE;CN=Max Rasmussen;ROLE=REQ-PARTICIPANT:MAILTO:maxm@example.com')
        self.assertEqual(
            c.parts(),
            ('ATTENDEE',
             Parameters({'ROLE': 'REQ-PARTICIPANT', 'CN': 'Max Rasmussen'}),
             'MAILTO:maxm@example.com')
        )
        self.assertEqual(
            c.to_ical(),
            'ATTENDEE;CN=Max Rasmussen;ROLE=REQ-PARTICIPANT:MAILTO:maxm@example.com'
        )

        # and back again
        # NOTE: we are quoting property values with spaces in it.
        parts = ('ATTENDEE',
                 Parameters({'ROLE': 'REQ-PARTICIPANT',
                             'CN': 'Max Rasmussen'}),
                 'MAILTO:maxm@example.com')
        self.assertEqual(
            Contentline.from_parts(parts),
            'ATTENDEE;CN="Max Rasmussen";ROLE=REQ-PARTICIPANT:MAILTO:maxm@example.com'
        )

        # and again
        parts = ('ATTENDEE', Parameters(), 'MAILTO:maxm@example.com')
        self.assertEqual(
            Contentline.from_parts(parts),
            'ATTENDEE:MAILTO:maxm@example.com'
        )

        # A value can also be any of the types defined in PropertyValues
        parts = ('ATTENDEE', Parameters(), vText('MAILTO:test@example.com'))
        self.assertEqual(
            Contentline.from_parts(parts),
            'ATTENDEE:MAILTO:test@example.com'
        )

        # A value in UTF-8
        parts = ('SUMMARY', Parameters(), vText('INternational char æ ø å'))
        self.assertEqual(
            Contentline.from_parts(parts),
            'SUMMARY:INternational char \xc3\xa6 \xc3\xb8 \xc3\xa5'
        )

        # A value can also be unicode
        parts = ('SUMMARY', Parameters(), vText(u'INternational char æ ø å'))
        self.assertEqual(
            Contentline.from_parts(parts),
            'SUMMARY:INternational char \xc3\xa6 \xc3\xb8 \xc3\xa5'
        )

        # Traversing could look like this.
        name, params, vals = c.parts()
        self.assertEqual(name, 'ATTENDEE')
        self.assertEqual(vals, 'MAILTO:maxm@example.com')
        self.assertEqual(
            params.items(),
            [('ROLE', 'REQ-PARTICIPANT'), ('CN', 'Max Rasmussen')]
        )

        # And the traditional failure
        with self.assertRaisesRegexp(
            ValueError,
            'Content line could not be parsed into parts'
        ):
            Contentline('ATTENDEE;maxm@example.com').parts()

        # Another failure:
        with self.assertRaisesRegexp(
            ValueError,
            'Content line could not be parsed into parts'
        ):
            Contentline(':maxm@example.com').parts()

        self.assertEqual(
            Contentline('key;param=:value').parts(),
            ('key', Parameters({'PARAM': ''}), 'value')
        )

        self.assertEqual(
            Contentline('key;param="pvalue":value').parts(),
            ('key', Parameters({'PARAM': 'pvalue'}), 'value')
        )

        # Should bomb on missing param:
        with self.assertRaisesRegexp(
            ValueError,
            'Content line could not be parsed into parts'
        ):
            Contentline.from_ical("k;:no param").parts()

        self.assertEqual(
            Contentline('key;param=pvalue:value', strict=False).parts(),
            ('key', Parameters({'PARAM': 'pvalue'}), 'value')
        )

        # If strict is set to True, uppercase param values that are not
        # double-quoted, this is because the spec says non-quoted params are
        # case-insensitive.
        self.assertEqual(
            Contentline('key;param=pvalue:value', strict=True).parts(),
            ('key', Parameters({'PARAM': 'PVALUE'}), 'value')
        )

        self.assertEqual(
            Contentline('key;param="pValue":value', strict=True).parts(),
            ('key', Parameters({'PARAM': 'pValue'}), 'value')
        )

    def test_fold_line(self):
        from icalendar.parser import foldline

        self.assertEqual(foldline('foo'), 'foo')
        self.assertEqual(
            foldline("Lorem ipsum dolor sit amet, consectetur adipiscing "
                     "elit. Vestibulum convallis imperdiet dui posuere."),
            ('Lorem ipsum dolor sit amet, consectetur adipiscing elit. '
             'Vestibulum conval\r\n lis imperdiet dui posuere.')
        )

        with self.assertRaises(AssertionError):
            foldline(u'привет', length=3)
        self.assertEqual(foldline('foobar', length=4), 'foo\r\n bar')
        self.assertEqual(
            foldline('Lorem ipsum dolor sit amet, consectetur adipiscing elit.'
                     ' Vestibulum convallis imperdiet dui posuere.'),
            ('Lorem ipsum dolor sit amet, consectetur adipiscing elit.'
             ' Vestibulum conval\r\n lis imperdiet dui posuere.')
        )
        self.assertEqual(
            foldline('DESCRIPTION:АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЬЫЪЭЮЯ'),
            'DESCRIPTION:АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЬЫЪЭ\r\n ЮЯ'
        )

    def test_value_double_quoting(self):
        from icalendar.parser import dQuote
        self.assertEqual(dQuote('Max'), 'Max')
        self.assertEqual(dQuote('Rasmussen, Max'), '"Rasmussen, Max"')
        self.assertEqual(dQuote('name:value'), '"name:value"')

    def test_q_split(self):
        from icalendar.parser import q_split
        self.assertEqual(q_split('Max,Moller,"Rasmussen, Max"'),
                         ['Max', 'Moller', '"Rasmussen, Max"'])

    def test_q_join(self):
        from icalendar.parser import q_join
        self.assertEqual(q_join(['Max', 'Moller', 'Rasmussen, Max']),
                         'Max,Moller,"Rasmussen, Max"')


def load_tests(loader=None, tests=None, pattern=None):
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(caselessdict))
    suite.addTest(doctest.DocTestSuite(parser))
    suite.addTest(doctest.DocTestSuite(prop))
    suite.addTest(doctest.DocTestSuite(cal))
    current_dir = os.path.dirname(__file__)
    for docfile in ['example.txt', 'groupscheduled.txt',
                    'small.txt', 'multiple.txt', 'recurrence.txt']:
        filename = os.path.abspath(os.path.join(current_dir, docfile))
        suite.addTest(
            doctest.DocFileSuite(
                docfile,
                optionflags=OPTIONFLAGS,
                globs={'__file__': filename}
            )
        )
    return suite
