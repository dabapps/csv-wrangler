from abc import ABCMeta, abstractmethod
import csv
from typing import List, Any, NamedTuple, Callable, Dict, TypeVar, Generic
from typing import Optional  # noqa
from functools import reduce
from django.http import HttpResponse


T = TypeVar('T')


class Header(Generic[T]):
    """
    Used for fishing fields out of data objects and providing them with labels
    """
    def __init__(self, label: str, callback: Callable[[T], str]) -> None:
        self.label = label
        self.callback = callback


class BaseExporter(metaclass=ABCMeta):
    """
    The root exporter class
    """

    header_order = None  # type: Optional[List[str]]

    @abstractmethod
    def to_list(self) -> List[List[str]]:  # pragma: no cover
        pass


class Exporter(Generic[T], BaseExporter, metaclass=ABCMeta):

    headers = []  # type: List[Header[T]]

    @abstractmethod
    def fetch_records(self) -> List[T]:  # pragma: no cover
        pass

    def get_headers(self) -> List[Header[T]]:
        return self.headers

    def get_sorted_headers(self) -> List[Header[T]]:
        return self.sort_headers(self.get_headers())

    def get_header_labels(self) -> List[str]:
        return [header.label for header in self.get_sorted_headers()]

    def sort_headers(self, headers: List[Header[T]]) -> List[Header[T]]:
        if not self.header_order:
            return headers

        return sorted(
            headers, key=lambda header:
                self.header_order.index(header.label) if header.label in self.header_order else len(self.header_order)
        )

    def to_list(self) -> List[List[str]]:
        records = self.fetch_records()
        headers = self.get_sorted_headers()
        lines = [
            [header.callback(record) for header in headers]
            for record in records
        ]
        return [self.get_header_labels()] + lines

    def as_response(self, filename: str='export') -> HttpResponse:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}.csv"'.format(filename)
        writer = csv.writer(response)
        [writer.writerow(row) for row in self.to_list()]
        return response


class MultiExporter(BaseExporter):

    exporters = None  # type: List[Exporter]

    def __init__(self, exporters: List[Exporter]) -> None:
        self.exporters = exporters

    def to_list(self) -> List[List[str]]:
        exportings = [exporter.to_list() for exporter in self.exporters]
        return reduce(lambda memo, exporting: exporting if memo == [] else memo + [[]] + exporting, exportings, [])


SimpleHeader = NamedTuple('Header', [('label', str), ('callback', Callable[[Any, str], str])])


class SimpleExporter(Exporter):

    headers = []  # type: List[Header[Dict[str, Any]]]
    fields = []  # type: List[str]
    data = []  # type: List[Dict[str, Any]]

    def __init__(self, fields: List[str], data: List[Dict[str, Any]]) -> None:
        self.data = data
        self.fields = fields

    def fetch_records(self) -> List[Dict[str, Any]]:
        return self.data

    def get_csv_headers(self) -> List[SimpleHeader]:
        return [
            SimpleHeader(label=field_name, callback=lambda record, field_name: str(record.get(field_name)) if record.get(field_name) is not None else '') for field_name in self.fields
        ]

    def get_csv_header_labels(self) -> List[str]:
        return [header.label for header in self.get_csv_headers()]

    def to_list(self) -> List[List[str]]:
        records = self.fetch_records()
        headers = self.get_csv_headers()
        lines = [
            [header.callback(record, header.label) for header in headers]
            for record in records
        ]
        return [self.get_csv_header_labels()] + lines


class PassthroughExporter(Exporter):

    data = []  # type: List[List[str]]

    def __init__(self, data: List[List[str]]) -> None:
        self.data = data

    def make_header(self, field_name: str, idx: int) -> Header[List[str]]:
        return Header(label=field_name, callback=lambda record: record[idx])

    def fetch_records(self) -> List[List[str]]:
        return self.data[1:]

    def get_headers(self) -> List[Header[List[str]]]:
        return [
            self.make_header(field_name, idx)
            for idx, field_name in enumerate(self.data[0])
        ]

