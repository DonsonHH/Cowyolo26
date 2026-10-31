"""Exact INT8 routing across structural graph operations; weights stay unchanged."""
import collections
import copy
import numpy as np


def optimize_integer_routes(executor):
    """Push a scalar quantizer through pure data routing, using exhaustive LUT leaves.

    Each leaf preserves the baseline's FP32 dequantize/activation/division/rounding
    order. Unconvertible leaves keep the original floating quantizer. Float users
    of a shared branch remain live; only dead nodes are removed afterwards.
    """
    original = executor.graph['nodes']
    producers = {o: n for n in original for o in n['outputs']}
    constants = executor.constants
    changes, replacements, additions = [], {}, {}
    route_ops = {'Concat', 'Split', 'Reshape', 'Transpose', 'Resize', 'Slice'}
    code = np.arange(256, dtype=np.uint8).view(np.int8)
    serial = 0

    def unique():
        nonlocal serial
        serial += 1
        return '__optimization_1_%d' % serial

    def fp32_values(dq, activated):
        scale, zero = (constants[k] for k in dq['inputs'][1:3])
        if scale.size != 1 or zero.size != 1 or zero.dtype != np.int8:
            raise ValueError('Only scalar signed INT8 quantization is supported')
        if executor.native:
            values = executor.native.dequantize(code, scale, zero)
            if activated:
                values = executor.native.silu(values, code, scale, zero)
        else:
            values = (code.astype(np.float32) - np.float32(zero.item())) * np.float32(scale.item())
            if activated:
                key = (float(scale.item()), int(zero.item()))
                table = next((executor.activation_tables['silu%d' % s['id']]
                              for s in executor.specs.values() if s['quantized'] and
                              (float(constants[s['quant']['output_scale']]),
                               int(constants[s['quant']['output_zp']])) == key), None)
                if table is None:
                    raise ValueError('No baseline activation LUT for this source')
                values = table.copy()
        return values

    for quantizer in original:
        if quantizer['op'] != 'QuantizeLinear':
            continue
        scale_name, zp_name = quantizer['inputs'][1:3]
        scale, zp = constants[scale_name], constants[zp_name]
        if scale.size != 1 or zp.size != 1 or zp.dtype != np.int8 or not float(scale.item()) > 0:
            continue
        pending, tables, cache = [], {}, {}
        beneficial = [0]

        def route(name):
            if name in cache:
                return cache[name]
            producer = producers.get(name)
            dq, activated = None, False
            if producer and producer['op'] == 'DequantizeLinear':
                dq = producer
            elif producer and producer['op'] == 'SiLU':
                candidate = producers.get(producer['inputs'][0])
                if candidate and candidate['op'] == 'DequantizeLinear':
                    dq, activated = candidate, True
            if dq is not None:
                try:
                    values = fp32_values(dq, activated)
                except ValueError:
                    dq = None
            if dq is not None:
                if executor.native:
                    table = executor.native.quantize(values, scale, zp)
                else:
                    table = np.clip(np.rint(values / np.float32(scale.item())) + int(zp.item()), -128, 127).astype(np.int8)
                output, table_name = unique(), unique()
                tables[table_name] = np.ascontiguousarray(table)
                identity = np.array_equal(table, code)
                pending.append(dict(name=output, op='Identity' if identity else 'Int8Lookup',
                                    inputs=[dq['inputs'][0]] if identity else [dq['inputs'][0], table_name],
                                    outputs=[output], attrs={}))
                cache[name] = output
                beneficial[0] += 1
                return output
            if producer and producer['op'] in route_ops:
                # These operators only select/reorder elements; nearest Resize is
                # the sole supported Resize mode in the baseline executor.
                if producer['op'] == 'Resize' and not (
                    producer['attrs'].get('mode') == 'nearest' and
                    producer['attrs'].get('coordinate_transformation_mode') == 'asymmetric' and
                    producer['attrs'].get('nearest_mode') == 'floor'):
                    producer = None
                else:
                    node = copy.deepcopy(producer)
                    node['name'] = unique()
                    node['inputs'] = ([route(i) for i in producer['inputs']] if producer['op'] == 'Concat'
                                      else [route(producer['inputs'][0])] + producer['inputs'][1:])
                    node['outputs'] = [unique() for _ in producer['outputs']]
                    for old, new in zip(producer['outputs'], node['outputs']):
                        cache[old] = new
                    pending.append(node)
                    return cache[name]
            # Preserve floating work at unsupported branches; no approximation.
            output = unique()
            pending.append(dict(name=output, op='QuantizeLinear', inputs=[name, scale_name, zp_name],
                                outputs=[output], attrs=copy.deepcopy(quantizer['attrs'])))
            cache[name] = output
            return output

        result = route(quantizer['inputs'][0])
        if not beneficial[0]:
            continue
        pending.append(dict(name=quantizer['name'], op='Identity', inputs=[result],
                            outputs=quantizer['outputs'], attrs={}))
        replacements[quantizer['name']] = pending
        additions.update(tables)
        changes.append(dict(quantizer=quantizer['name'], integer_leaves=beneficial[0]))

    compiled = [candidate for node in original for candidate in replacements.get(node['name'], [node])]
    # SiLU's native LUT reads the INT8 source in addition to its explicit float input.
    all_producers = {o: n for n in compiled for o in n['outputs']}

    def dependencies(node):
        names = list(node['inputs'])
        if node['op'] == 'SiLU':
            dq = all_producers.get(node['inputs'][0])
            if dq and dq['op'] == 'DequantizeLinear':
                names.append(dq['inputs'][0])
        return names

    live = set()

    def retain(name):
        node = all_producers.get(name)
        if node is None or node['name'] in live:
            return
        live.add(node['name'])
        for source in dependencies(node):
            retain(source)

    retain(executor.graph['output'])
    compiled = [node for node in compiled if node['name'] in live]
    # Routing inserted at a quantizer's location may depend on shared generated
    # values only within that location; original graph is topologically ordered.
    ready = set(constants) | {executor.graph['input']} | set(additions)
    for node in compiled:
        missing = set(i for i in dependencies(node) if i) - ready
        if missing:
            raise RuntimeError('Integer routing violates graph order: %s: %s' % (node['name'], missing))
        ready.update(node['outputs'])
    constants.update(additions)
    executor.graph['nodes'] = compiled
    executor.producers = {o: n for n in compiled for o in n['outputs']}
    executor.required_inputs = {n['name']: dependencies(n) for n in compiled}
    executor.use_counts = collections.Counter(i for v in executor.required_inputs.values() for i in v if i)
    executor.optimization_summary = dict(original_nodes=len(original), optimized_nodes=len(compiled),
                                        quantizer_routes=changes, lut_bytes=sum(t.nbytes for t in additions.values()),
                                        original_ops=dict(collections.Counter(n['op'] for n in original)),
                                        optimized_ops=dict(collections.Counter(n['op'] for n in compiled)))
    return executor.optimization_summary
