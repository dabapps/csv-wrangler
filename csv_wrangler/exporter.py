from abc import ABCMeta, abstractmethod
import csv
from typing import List, Any, NamedTuple, Callable, Dict, TypeVar, Generic, Generator
from typing import Optional  # noqa
from functools import reduce
from django.http import HttpResponse, StreamingHttpResponse


T = TypeVar('T')


class Header(Generic[T]):
    """
    Used for fishing fields out of data objects and providing them with labels
    """
    def __init__(self, label: str, callback: Callable[[T], str]) -> None:
        self.label = label
        self.callback = callback


class Echo:
    """
    An object that implements just the write method of the file-like
    interface.
    https://docs.djangoproject.com/en/1.10/howto/outputting-csv/
    """
    def write(self, value):
        """Write the value by returning it, instead of storing in a buffer."""
        return value


class BaseExporter(metaclass=ABCMeta):
    """
    The root exporter class
    """

    header_order = None  # type: Optional[List[str]]
    CONTENT_TYPE = 'text/csv' # type: str

    @abstractmethod
    def to_iter(self) -> Generator[List[str], None, None]:  # pragma: no cover
        pass

    def to_list(self) -> List[List[str]]:
        return list(self.to_iter())

    def format_content_disposition(self, filename: str='export') -> str:
        return 'attachment; filename="{}.csv"'.format(filename)

    def as_response(self, filename: str) -> HttpResponse:
        response = HttpResponse(content_type=self.CONTENT_TYPE)
        response['Content-Disposition'] = self.format_content_disposition(filename)
        writer = csv.writer(response)
        [writer.writerow(row) for row in self.to_list()]
        return response

    def as_streamed_response(self, filename: str) -> StreamingHttpResponse:
        writer = csv.writer(Echo())
        response = StreamingHttpResponse(
            (writer.writerow(row) for row in self.to_iter()),
            content_type=self.CONTENT_TYPE
        )
        response['Content-Disposition'] = self.format_content_disposition(filename)
        return response


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

    def to_iter(self) -> Generator[List[str], None, None]:
        records = self.fetch_records()
        headers = self.get_sorted_headers()
        yield self.get_header_labels()
        for record in records:
            yield [header.callback(record) for header in headers]


class MultiExporter(BaseExporter):

    exporters = None  # type: List[Exporter]

    def __init__(self, exporters: List[Exporter]) -> None:
        self.exporters = exporters

    def to_list(self) -> List[List[str]]:
        exportings = [exporter.to_list() for exporter in self.exporters]
        return reduce(lambda memo, exporting: exporting if memo == [] else memo + [[]] + exporting, exportings, [])

    def to_iter(self) -> Generator[List[str], None, None]:
        for exporter in self.exporters:
            yield from exporter.to_iter()
            if exporter != self.exporters[-1]:
                yield []


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
            SimpleHeader(
                label=field_name,
                callback=lambda record, field_name: str(record.get(field_name)) if record.get(field_name) is not None else ''
            ) for field_name in self.fields
        ]

    def get_csv_header_labels(self) -> List[str]:
        return [header.label for header in self.get_csv_headers()]

    def to_iter(self) -> Generator[List[str], None, None]:
        records = self.fetch_records()
        headers = self.get_csv_headers()
        yield self.get_csv_header_labels()
        for record in records:
            yield [header.callback(record, header.label) for header in headers]


class PassthroughExporter(BaseExporter):

    data = []  # type: List[List[str]]

    def __init__(self, data: List[List[str]]) -> None:
        self.data = data

    def to_iter(self) -> Generator[List[str], None, None]:
        yield from self.data
