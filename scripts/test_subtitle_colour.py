"""Focused regressions for Arabic subtitle colours and visual sample coverage.

Run: python -X utf8 scripts/test_subtitle_colour.py
No third-party packages. Real video output still requires visual inspection.
"""
from pathlib import Path
import contextlib
import io
import re
import tempfile
from types import SimpleNamespace
import unittest

import captions
import embed_subtitles


class ColourRuns(unittest.TestCase):
    def test_multiword_phrase_stays_one_run(self):
        m = captions.INF_MARK
        self.assertEqual(captions._colour_line(m+'ليس '+m+'عبثاً '+m+'أن', '#FFC857'),
                         '<font color="#FFC857">ليس عبثاً أن</font>')

    def test_known_words_separate_inferred_runs(self):
        m = captions.INF_MARK
        self.assertEqual(captions._colour_line('إلى '+m+'النفس أم '+m+'الدماغ؟', '#FFC857'),
                         'إلى <font color="#FFC857">النفس</font> أم <font color="#FFC857">الدماغ؟</font>')

    def test_plain_words_are_unchanged(self):
        text = 'حين نختار شريكاً للحياة، هل نصغي؟'
        self.assertEqual(captions._colour_line(text, '#FFC857'), text)

    def test_lines_do_not_share_colour_tags(self):
        m = captions.INF_MARK
        lines = [m+'شريكاً '+m+'للحياة،', m+'هل '+m+'نصغي؟']
        result = [captions._colour_line(line, '#FFC857') for line in lines]
        self.assertTrue(all(line.count('<font') == line.count('</font>') == 1 for line in result))
        self.assertEqual(re.sub(r'<[^>]+>', '', '\n'.join(result)), 'شريكاً للحياة،\nهل نصغي؟')

    def test_digits_punctuation_and_custom_colour(self):
        m = captions.INF_MARK
        self.assertEqual(captions._colour_line(m+'350 '+m+'سنة، ثم 100%', '#123456'),
                         '<font color="#123456">350 سنة،</font> ثم 100%')

    def test_full_srt_preserves_order_timing_and_colour_coverage(self):
        with tempfile.TemporaryDirectory(prefix='lzr-colour-test-') as tmp:
            root = Path(tmp); source = root/'translated.md'; output = root/'arabic.srt'
            source.write_text('<!-- s0001 00:00:01.000-00:00:11.000 -->\n'
                              'حين نختار {{شريكاً للحياة،}} هل نصغي إلى {{النفس}} أم الدماغ؟\n', encoding='utf-8')
            args = SimpleNamespace(translated=str(source), out=str(output), width=36,
                                   keep_periods=False, inferred_color='#FFC857')
            with contextlib.redirect_stdout(io.StringIO()):
                captions.cmd_build(args)
            raw = output.read_text(encoding='utf-8-sig')
            cues = captions.parse_cues(raw)
            words = ' '.join(c[2] for c in cues).replace('\u200f', '').split()
            self.assertEqual(words, 'حين نختار شريكاً للحياة، هل نصغي إلى النفس أم الدماغ؟'.split())
            coloured = [word for span in re.findall(r'<font[^>]+>(.*?)</font>', raw) for word in span.split()]
            self.assertEqual(coloured, ['شريكاً', 'للحياة،', 'النفس'])
            self.assertEqual(cues[0][0], 1.0)
            self.assertEqual(cues[-1][1], 11.0)
            self.assertTrue(all(a[1] <= b[0] for a, b in zip(cues, cues[1:])))
            self.assertNotRegex(raw, r'</font>[ \t]+<font color="#FFC857">')
            self.assertTrue(output.read_bytes().startswith(b'\xef\xbb\xbf'))


class FrameCoverage(unittest.TestCase):
    def fixture(self, bodies):
        return '\r\n\r\n'.join(f'{i+1}\r\n{captions.fmt(i*3, True)} --> '
                                  f'{captions.fmt(i*3+2, True)}\r\n{body}'
                                  for i, body in enumerate(bodies))

    def test_mixed_multiword_cues_are_added_to_general_coverage(self):
        bodies = ['نص أبيض']*12
        bodies[1] = 'كلمة <font color="#FFC857">واحدة</font>'
        bodies[2] = 'حين نختار <font color="#FFC857">شريكاً للحياة،</font> هل نصغي'
        bodies[4] = '\u200f<font color="#FFC857">كل السطر ملوّن</font>'
        bodies[8] = '<font color="#FFC857">ليس عبثاً أن</font> الاكتئاب والانتحار'
        picks = embed_subtitles._frame_samples(self.fixture(bodies))
        self.assertEqual(picks, [(3, 5), (18, 20), (30, 32), (6, 8), (24, 26)])

    def test_plain_cues_keep_beginning_middle_end(self):
        self.assertEqual(embed_subtitles._frame_samples(self.fixture(['نص أبيض']*12)),
                         [(3, 5), (18, 20), (30, 32)])

    def test_one_cue_is_not_duplicated(self):
        self.assertEqual(embed_subtitles._frame_samples(self.fixture(['<font color="#FFC857">عبارة ملوّنة</font> ونص'])),
                         [(0, 2)])

    def test_no_cues(self):
        self.assertEqual(embed_subtitles._frame_samples(''), [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
