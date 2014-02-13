import schema


def soft_schema(**kwargs):
    """
        soft_schema(k1=schema1, k2=schema2, ...)

    Returns a schema for dicts having the keys k1, k2, ... and possibly other
    string keys not explicitly stated. The schema for the values is the one
    provided (i.e. schema for k2 is Schema(schema2)). Other keys have
    Schema(object).

    If one of the inner schemas given is a dict, it's interpreted as a soft
    dictionary schema too.
    """

    def _transform(d):
        result = d.copy()
        for k, v in result.items():
            if isinstance(v, dict):
                result[k] = _transform(v)
        result[schema.Optional(str)] = object
        return result

    return schema.Schema(_transform(kwargs))


class Feature(object):

    input_schema = schema.Schema(object)
    output_schema = schema.Schema(object)

    def __call__(self, data_point):
        try:
            data_point = self.input_schema.validate(data_point)
        except schema.SchemaError as e:
            raise ValueError(e)
        result = self._evaluate(data_point)
        try:
            return self.output_schema.validate(result)
        except schema.SchemaError as e:
            raise ValueError(e)

    def _evaluate(self, data_point):
        return None
