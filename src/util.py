import collections
import logging
import hashlib
import os

CHUNK_SIZE = 1024**2


def sha256_hash(filepath, block_size=CHUNK_SIZE):
    hasher = hashlib.sha256()
    assert block_size > 0, ("hash block size must be greater than zero.")
    with open(filepath, 'rb') as hash_file:
        for block in iter(lambda: hash_file.read(block_size), b''):
            hasher.update(block)
    logging.info('File hash: %s (%s)' % (hasher.hexdigest(), filepath))
    return hasher.hexdigest()


def list_files(directory):
    sep = os.path.sep
    # using os.path.join to prevent an additional
    # os.path.sep if directory already ends with it
    root = os.path.join(directory, '')
    for directory, _, files in os.walk(directory):
        for file in files:
            full_path = os.path.join(directory, file)
            relative_path = os.path.relpath(full_path, root).replace(sep, '/')
            yield full_path, relative_path


def tupperware(mapping):
    """ Convert mappings to 'tupperwares' recursively.
    Lets you use dicts like they're JavaScript Object Literals (~=JSON)...
    It recursively turns mappings (dictionaries) into namedtuples.
    Thus, you can cheaply create an object whose attributes are accessible
    by dotted notation (all the way down).
    Use cases:
        * Fake objects (useful for dependency injection when you're making
         fakes/stubs that are simpler than proper mocks)
        * Storing data (like fixtures) in a structured way, in Python code
        (data whose initial definition reads nicely like JSON). You could do
        this with dictionaries, but namedtuples are immutable, and their
        dotted notation can be clearer in some contexts.
    .. doctest::
        >>> t = tupperware({
        ...     'foo': 'bar',
        ...     'baz': {'qux': 'quux'},
        ...     'tito': {
        ...             'tata': 'tutu',
        ...             'totoro': 'tots',
        ...             'frobnicator': ['this', 'is', 'not', 'a', 'mapping']
        ...     }
        ... })
        >>> t # doctest: +ELLIPSIS
        Tupperware(tito=Tupperware(...), foo='bar', baz=Tupperware(qux='quux'))
        >>> t.tito # doctest: +ELLIPSIS
        Tupperware(frobnicator=[...], tata='tutu', totoro='tots')
        >>> t.tito.tata
        'tutu'
        >>> t.tito.frobnicator
        ['this', 'is', 'not', 'a', 'mapping']
        >>> t.foo
        'bar'
        >>> t.baz.qux
        'quux'
    Args:
        mapping: An object that might be a mapping. If it's a mapping, convert
        it (and all of its contents that are mappings) to namedtuples
        (called 'Tupperwares').
    Returns:
        A tupperware (a namedtuple (of namedtuples (of namedtuples (...)))).
        If argument is not a mapping, it just returns it (this enables the
        recursion).
    """

    if (isinstance(mapping, collections.Mapping) and
            not isinstance(mapping, ProtectedDict)):
        for key, value in mapping.items():
            mapping[key] = tupperware(value)
        return namedtuple_from_mapping(mapping)
    return mapping


def namedtuple_from_mapping(mapping, name="Tupperware"):
    this_namedtuple_maker = collections.namedtuple(name, mapping.keys())
    return this_namedtuple_maker(**mapping)


class ProtectedDict(collections.UserDict):
    """ A class that exists just to tell `tupperware` not to eat it.
    `tupperware` eats all dicts you give it, recursively; but what if you
    actually want a dictionary in there? This will stop it. Just do
    ProtectedDict({...}) or ProtectedDict(kwarg=foo).
    """
