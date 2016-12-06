from unittest import TestCase
from typing import NamedTuple
from typing import List, Any
from csv_wrangler.exporter import Exporter, Header, MultiExporter, SimpleExporter, PassthroughExporter


DummyData = NamedTuple('DummyData', [('a', str), ('b', int), ('c', float)])


class DummyExporter(Exporter):

    headers = [
        Header(label='a', callback=lambda x: x.a),
        Header(label='b', callback=lambda x: str(x.b)),
        Header(label='c', callback=lambda x: str(x.c)),
    ]  # type: List[Header[DummyData]]

    def fetch_records(self) -> List[DummyData]:
        return [
            DummyData(a='a', b=1, c=1.0),
            DummyData(a='b', b=2, c=2.0),
            DummyData(a='c', b=3, c=3.0),
        ]


class SecondDummyExporter(Exporter):

    headers = [
        Header(label='dummy', callback=lambda x: x),
    ]  # type: List[Header[str]]

    def fetch_records(self) -> List[str]:
        return [
            'llama',
            'drama'
        ]


class ExporterTestCase(TestCase):

    def setUp(self) -> None:
        self.exporter = DummyExporter()

    def test_to_list(self) -> None:
        results = self.exporter.to_list()
        self.assertEqual(results[0], ['a', 'b', 'c'])
        self.assertEqual(results[1], ['a', '1', '1.0'])
        self.assertEqual(results[2], ['b', '2', '2.0'])
        self.assertEqual(results[3], ['c', '3', '3.0'])

    def test_ordering(self) -> None:
        self.exporter.header_order = ['c', 'b', 'a']
        results = self.exporter.to_list()
        self.assertEqual(results[0], ['c', 'b', 'a'])
        self.assertEqual(results[1], ['1.0', '1', 'a'])
        self.assertEqual(results[2], ['2.0', '2', 'b'])
        self.assertEqual(results[3], ['3.0', '3', 'c'])

    def test_partial_ordering(self) -> None:
        self.exporter.header_order = ['b', 'a']
        results = self.exporter.to_list()
        self.assertEqual(results[0], ['b', 'a', 'c'])
        self.assertEqual(results[1], ['1', 'a', '1.0'])
        self.assertEqual(results[2], ['2', 'b', '2.0'])
        self.assertEqual(results[3], ['3', 'c', '3.0'])

    def test_as_response(self) -> None:
        filename = 'hello'
        results = self.exporter.as_response(filename)
        self.assertEqual(results['content-type'], 'text/csv')
        self.assertEqual(results['Content-Disposition'], 'attachment; filename="{}.csv"'.format(filename))
        self.assertEqual(str(results.content, 'utf-8'), '\r\n'.join([
            ','.join(row)
            for row
            in self.exporter.to_list()
        ]) + '\r\n')


class MultiExporterTestCase(TestCase):

    def setUp(self) -> None:
        self.exporter = DummyExporter()
        self.exporter_2 = SecondDummyExporter()

    def test_multiple_exporters(self) -> None:
        multi_exporter = MultiExporter([
            self.exporter,
            self.exporter_2
        ])
        results = multi_exporter.to_list()
        self.assertEqual(results[0], ['a', 'b', 'c'])
        self.assertEqual(results[1], ['a', '1', '1.0'])
        self.assertEqual(results[2], ['b', '2', '2.0'])
        self.assertEqual(results[3], ['c', '3', '3.0'])
        self.assertEqual(results[4], [])
        self.assertEqual(results[5], ['dummy'])
        self.assertEqual(results[6], ['llama'])
        self.assertEqual(results[7], ['drama'])


class SimpleExporterTestCase(TestCase):

    def test_simple_exporter(self) -> None:
        exporter = SimpleExporter(['a', 'b', 'c'], [{
            'a': 5,
            'b': 10,
            'c': 15
        }])
        results = exporter.to_list()
        self.assertEqual(results[0], ['a', 'b', 'c'])
        self.assertEqual(results[1], ['5', '10', '15'])


class PassthroughExporterTestCase(TestCase):

    def test_passthrough_to_list(self) -> None:
        exporter = PassthroughExporter([
            ['a', 'b', 'c'],
            ['1', '2', '3'],
            ['2', '3', '4'],
        ])
        results = exporter.to_list()
        self.assertEqual(results[0], ['a', 'b', 'c'])
        self.assertEqual(results[1], ['1', '2', '3'])
        self.assertEqual(results[2], ['2', '3', '4'])
