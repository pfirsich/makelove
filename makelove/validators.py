class Section:
    def __init__(self, params):
        self.params = params

    def validate(self, obj):
        if not isinstance(obj, dict):
            raise ValueError
        for param in obj:
            if param not in self.params:
                raise ValueError(f"Unknown parameter '{param}'")
            try:
                self.params[param].validate(obj[param])
            except ValueError as exc:
                if len(str(exc)) == 0:
                    raise ValueError(
                        f"Invalid value for parameter '{param}'. Expected: {self.params[param].description()}"
                    )
                else:
                    raise
        return obj

    def description(self):
        return "Section"


class Bool:
    def validate(self, obj):
        if not isinstance(obj, bool):
            raise ValueError
        return obj

    def description(self):
        return "Boolean"


class String:
    def validate(self, obj):
        if not isinstance(obj, str):
            raise ValueError
        return obj

    def description(self):
        return "String"


class Any:
    def validate(self, obj):
        return obj

    def description(self):
        return "Any value"


class Choice:
    def __init__(self, *choices):
        self.choices = choices

    def validate(self, obj):
        if obj not in self.choices:
            raise ValueError
        return obj

    def description(self):
        return "One of [{}]".format(", ".join(self.choices))


# This validator is mostly used for documentation, since on Linux
# for example almost anything could be a path
class Path:
    def validate(self, obj):
        if not isinstance(obj, str):
            raise ValueError
        return obj

    def description(self):
        return "Path"


# Same as path
class Command:
    def validate(self, obj):
        if not isinstance(obj, str):
            raise ValueError
        return obj

    def description(self):
        return "Command"


class List:
    def __init__(self, value_validator):
        self.value_validator = value_validator

    def validate(self, obj):
        if not isinstance(obj, list):
            raise ValueError
        for value in obj:
            self.value_validator.validate(value)
        return obj

    def description(self):
        return f"List({self.value_validator.description()})"


class Dict:
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
        return f"Dictionary(key = {self.key_validator.description()}, value = {self.value_validator.description()})"


class Option:
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
