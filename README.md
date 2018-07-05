[![Build Status](https://travis-ci.com/dabapps/csv-wrangler.svg?token=apzD3FKHpTNKHAtAu9xC&branch=master)](https://travis-ci.com/dabapps/csv-wrangler)
CSV Wrangler
===================
Statically typed Python 3 CSV generation helpers.
Write nicely typed CSV handling logic, with reorderable headers!

Settings
--------

Currently not on `pip`, as this isn't quite ready to hit the big time.  Whack this into your requirements file:

```
    git+git://github.com/dabapps/csv-wrangler.git@v0.1.2#egg=csv-wrangler
```

And then add it to your `INSTALLED_APPS`

```python
    'csv_wrangler'
```

Usage
-----

Check `test_exporter.py` for some examples of it in action.

Generally, you'll want to subclass `Exporter` and provide two required changes, `headers` and `fetch_records`. You'll also want a way to get data into the exporter - override `__init__` for this.

You'll also need to specify a type for your headers to run over. We recommend you go with something like a `NamedTuple`, but any blob of data that is meaningful to you will do.

For example, we'll start with a simple type:

```python
    Llama = NamedTuple('Llama', [('name': str), ('fluff_factor': int)])
```

Now, we'll need our derived class:

```python
class LlamaExporter(Exporter):

    headers = [
        Header(label='name', callback=lambda llama: llama.name,
        Header(label='fluff_factor', callback=lambda llama: str(llama.fluff_factor)),
        Header(label='name_length', callback=lambda llama: str(len(llama.name))),
    ]  # type: List[Header[Llama]]

    def __init__(self, llamas: List[Llama]) -> None:
        self.data = llamas

    def fetch_records(self) -> List[Llama]:
        return self.data
```

Here, our `fetch_records` is just spitting the data straight to the headers for unpacking. If you have more complex requirements, `fetch_records` is a good place to convert to a list of easily accessed blobs of data.

Note that we specify the type of the header for `headers`. This allows the typechecker to find out quickly if any of your headers are accessing data incorrectly.

Now, we can use it. We have several methods for getting data out:

`to_list` will convert the data to a list of lists of strings (allowing you to pass it to whatever other CSV handling options you want):

```python
LlamaExporter(my_llamas).to_list()
```

whereas `as_response` will turn it into a prepared HttpResponse for returning from one of your views:

```python
LlamaExporter.as_response('my_llamas')
```

If your CSV is large, and takes a long time to generate, you should use a generator, or stream the response. `to_iter` and `to_streamed_response` are the generator_counterparts to the above methods, working in exactly the same way, just returning a generator and a `HttpStreamedResponse` respectively. By default, `to_list` calls `to_iter`, so if you need to do anything custom, it's best to do it in `to_iter`.

You can also provide an ordering to the headers, if you want.  Simply assign a list of strings to `header_order` and when the data is unpacked, those headers who's labels match these will be placed in that order.

```python
LlamaExporter.header_order = ['name', 'name_length', 'fluff_factor']
```

If you end up in a situation where you need to output multiple CSV tables at once, you can use `MultiExporter`

```python
MultiExporter(
    LlamaExporter(my_llamas),
    AlpacaExporter(my_alpacas)
).to_list()
```

This will append the second CSV after the first, with a single blank line between it.

We also provide a `SimpleExporter`, for extracting information from a list of dictionaries, and a `PassthroughExporter`, for when you already have a List of Lists of Strings.

Have fun!
