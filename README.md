CSV Wrangler
===================
[![Build Status](https://travis-ci.com/dabapps/csv-wrangler.svg?token=apzD3FKHpTNKHAtAu9xC&branch=master)](https://travis-ci.com/dabapps/csv-wrangler)
[![pypi release](https://img.shields.io/pypi/v/csv-wrangler.svg)](https://pypi.python.org/pypi/csv-wrangler)

Statically-typed Python 3 CSV generation helpers.
Write nicely typed CSV handling logic, with reorderable headers!

## Getting Started

### Installation

Install with `pip`

    pip install csv-wrangler

Add `csv_wrangler` to your installed apps

    INSTALLED_APPS = (
        ...
        'csv_wrangler',
    )

## Usage

### Create an Exporter

Generally, you'll want to subclass `Exporter` and provide two required changes, `headers` and `fetch_records`. You'll also want a way to get data into the exporter - override `__init__` for this.

You'll also need to specify a type for your headers to run over. We recommend you go with something like a `NamedTuple`, but any blob of data that is meaningful to you will do.

Let's create a `llama_exporter.py`:

```python
from typing import List
from csv_wrangler.exporter import Exporter, Header
from .models import Llama

# We start by defining Llama's type
Llama = NamedTuple('Llama', [('first_name': str), ('last_name': str), ('fluff_factor': int)])

# We can define a helper function if needed
def get_full_name(llama):
    return "{} {}".format(llama.first_name, llama.last_name)


# And we'll need our derived class
class LlamaExporter(Exporter):

    headers = [
        Header(label='name', callback=get_full_name),
        Header(label='fluff_factor', callback=lambda llama: str(llama.fluff_factor)),
        Header(label='first_name_length', callback=lambda llama: str(len(llama.first_name))),
    ]  # type: List[Header[Llama]]

    def __init__(self, llamas: List[Llama]) -> None:
        self.data = llamas

    def fetch_records(self) -> List[Llama]:
        return self.data
```

Here, our `fetch_records` is just spitting the data straight to the headers for unpacking. If you have more complex requirements, `fetch_records` is a good place to convert to a list of easily accessed blobs of data.

Note that we specify the type of the header for `headers`. This allows the typechecker to find out quickly if any of your headers are accessing data incorrectly.

When you want to access `self` in `headers`, you can use the function `get_headers` instead. (Try to avoid using this function if not necessary, as it will slow things down) For example, the `LlamaExporter` could look like this:

```python
class LlamaExporter(Exporter):

    def __init__(self, llamas: List[Llama]) -> None:
        self.data = llamas
        self.llamas_are_cute = True

    def fetch_records(self) -> List[Llama]:
        return self.data

    def get_headers(self) -> List[Header[Llama]]:
        return [
            Header(label='name', callback=get_full_name),
            Header(label='fluff_factor', callback=lambda llama: str(llama.fluff_factor)),
            Header(label='first_name_length', callback=lambda llama: str(len(llama.first_name))),
            Header(label='are_llamas_cute?', callback=lambda llama: str(self.llamas_are_cute)),
        ]
```

### Use the Exporter
Now, we can use it. We have several methods for getting data out:

`to_list` will convert the data to a list of lists of strings (allowing you to pass it to whatever other CSV handling options you want):

```python
from .exporters import LlamaExporter
from .models import Llama
...


def some_function_where_i_want_to_use_csv_data():
    my_llamas = Llama.objects.all()
    exporter = LLamaExporter(llamas=my_llamas)
    data = exporter.to_list()
    # perhaps pass data to other CSV handling options
    return
```

whereas `as_response` will turn it into a prepared HttpResponse for returning from one of your views:

```python
from django.views import View
from .exporters import LlamaExporter
from .models import Llama
...


class LlamaCsvExportView(View):

    def get(self, request):
        my_llamas = Llama.objects.all()
        exporter = LLamaExporter(llamas=my_llamas)
        return exporter.as_response(filename='my_llamas')
```

If you simply want to get access to the CSV rows as strings, you can use the `as_csv_rows` method, which returns each row of the CSV in a list.

When you want to setup and endpoint for getting the csv, this'll be as simple as adding the following to `urls.py`

```python
url(r'^llamas/csv/$', LlamaCsvExportView.as_view(), name="llama-csv")
```

Other nice features
-----------------
### Streamed Response

If your CSV is large, and takes a long time to generate, you should use a generator, or stream the response. `to_iter` and `as_streamed_response` are the generator_counterparts to the above methods, working in exactly the same way, just returning a generator and a `HttpStreamedResponse` respectively. By default, `to_list` calls `to_iter`, so if you need to do anything custom, it's best to do it in `to_iter`.

### Save to file-like object

Sometimes, you may need to save the CSV rather than return it as a response. To do this, you can pass a file-like object to the `save` method. The CSV will be saved into the file, without loading the whole thing into memory first.

This can be combined with [`StringIO`](https://docs.python.org/3/library/io.html#io.StringIO) to access the entire CSV as a string (not recommended for large CSVs)

### Ordering headers
You can also provide an ordering to the headers, if you want.  Simply assign a list of strings to `header_order` and when the data is unpacked, those headers who's labels match these will be placed in that order.

So for example in your view, you can add:

```python
exporter = LLamaExporter(llamas=my_llamas)
exporter.header_order = ['name', 'first_name_length', 'fluff_factor']
```

### Mulitple CSVs
If you end up in a situation where you need to output multiple CSV tables at once, you can use `MultiExporter`

```python
exporter = MultiExporter(
    LlamaExporter(my_llamas),
    AlpacaExporter(my_alpacas)
)
exporter.to_list()
```

This will append the second CSV after the first, with a single blank line between it.

### Simple Exporter
We also provide a `SimpleExporter`, for extracting information from a list of dictionaries.

Say you have a list of dictionaries

```python
dicts = [
    {
        'name': 'Lama glama',
        'fluff_factor': 9,
        'is_cute?': 'yes'
    },{
        'name': 'Lama guanicoe',
        'fluff_factor': 2,
    }
]
```
Then you can create a simple exporter with `headers = ['name', 'fluff_factor', 'is_cute?']` as `exporter = SimpleExporter(headers, dicts)`.
Your `exporter.to_list()` would be `[['name', 'fluff_factor', 'is_cute?'], ['Lama glama', '9', 'yes'], ['Lama guanicoe', '2', '']]`.

### Passthrough Exporter
You can use the `PassthroughExporter` when you already have a List of Lists of Strings.

So when you have the exact data you want to put in your CSV, you can simply create an exporter like this
```python
exporter = PassthroughExporter([
    ['name', 'fluff factor', 'is cute?'],
    ['Alpaca LLama', '10', 'yes'],
    ['Guanaco Llama', '6', 'no'],
])
```

Have fun!

## Code of conduct

For guidelines regarding the code of conduct when contributing to this repository please review [https://www.dabapps.com/open-source/code-of-conduct/](https://www.dabapps.com/open-source/code-of-conduct/)
