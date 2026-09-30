"""Strict, bounded decoding at untrusted JSON boundaries (no state or repair)."""
import json
import math


def loads(raw, *, max_bytes=4 * 1024 * 1024, max_depth=64):
    if len(raw) > max_bytes:
        raise ValueError('JSON size limit exceeded')
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode('utf-8')
    if len(raw.encode('utf-8')) > max_bytes:
        raise ValueError('JSON size limit exceeded')
    depth, quoted, escaped = 0, False, False
    for char in raw:
        if quoted:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in '[{':
            depth += 1
            if depth > max_depth:
                raise ValueError('JSON depth limit exceeded')
        elif char in ']}':
            depth -= 1

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = value
        return result

    def finite(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError('Non-finite JSON number')
        return number

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=finite, parse_float=finite)


def read(path):
    # Fixtures contain both prompt and response, so have a separate envelope bound.
    limit = 16 * 1024 * 1024
    with path.open('rb') as stream:
        return loads(stream.read(limit + 1), max_bytes=limit, max_depth=96)
