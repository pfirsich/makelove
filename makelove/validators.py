class Section(object):
    def __init__(self, params):
        self.params = params

    def validate(self, obj):
        if not isinstance(obj, dict):
            raise ValueError
        for param in obj:
            if param not in self.params:
                raise ValueError("Unknown parameter '{}'".format(param))
            try:
                self.params[param].validate(obj[param])
            except ValueError as exc:
                if len(str(exc)) == 0:
                    raise ValueError(
                        "Invalid value for parameter '{}'. Expected: {}".format(
                            param, self.params[param].description()
                        )
                    )
                else:
                    raise
        return obj

    def description(self):
        return "Section"


class Bool(object):
    def validate(self, obj):
        if not isinstance(obj, bool):
            raise ValueError
        return obj

    def description(self):
        return "Boolean"


class String(object):
    def validate(self, obj):
        if not isinstance(obj, str):
            raise ValueError
        return obj

    def description(self):
        return "String"


class Any(object):
    def validate(self, obj):
        return obj

    def description(self):
        return "Any value"


class Choice(object):
    def __init__(self, *choices):
        self.choices = choices

    def validate(self, obj):
        if not obj in self.choices:
            raise ValueError
        return obj

    def description(self):
        return "One of [{}]".format(", ".join(self.choices))


# This validator is mostly used for documentation, since on Linux
# for example almost anything could be a path
class Path(object):
    def validate(self, obj):
        if not isinstance(obj, str):
            raise ValueError
        return obj

    def description(self):
        return "Path"


# Same as path
class Command(object):
    def validate(self, obj):
        if not isinstance(obj, str):
            raise ValueError
        return obj

    def description(self):
        return "Command"


class List(object):
    def __init__(self, value_validator):
        self.value_validator = value_validator

    def validate(self, obj):
        if not isinstance(obj, list):
            raise ValueError
        for value in obj:
            self.value_validator.validate(value)
        return obj

    def description(self):
        return "List({})".format(self.value_validator.description())


class Dict(object):
    def __init__(self, key_validator, value_validator):
        self.key_validator = key_validator
        self.value_validator = value_validator

    def validate(self, obj):
        if not isinstance(obj, dict):
            raise ValueError
        for k, v in obj.items():
            self.key_validator.validate(k)
            self.value_validator.validate(v)
        return obj

    def description(self):
        return "Dictionary(key = {}, value = {})".format(
            self.key_validator.description(), self.value_validator.description()
        )


class Option(object):
    def __init__(self, *option_validators):
        self.option_validators = option_validators

    def validate(self, obj):
        for option in self.option_validators:
            try:
                option.validate(obj)
                return obj
            except ValueError:
                pass
        raise ValueError

    def description(self):
        return "Option({})".format(
            ", ".join(option.description() for option in self.option_validators)
        )


def ValueOrList(value_validator):
    return Option(value_validator, List(value_validator))
