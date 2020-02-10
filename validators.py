class LoveVersion(object):
    def __init__(self):
        pass

    def validate_str(self, s):
        if not all(part.isdigit() for part in s.split(".")):
            raise ValueError
        return s

    def validate_obj(self, obj):
        self.validate_str(obj)
        return obj


class List(object):
    def __init__(self, value_validator):
        self.value_validator = value_validator

    def validate_str(self, s):
        return [self.value_validator.validate_str(part) for part in s.split(",")]

    def validate_obj(self, obj):
        if not isinstance(obj, list):
            raise ValueError
        for value in obj:
            self.value_validator.validate_obj(value)
        return obj


class Choice(object):
    def __init__(self, *choices):
        self.choices = choices

    def validate_str(self, s):
        if not s in self.choices:
            raise ValueError
        return s

    def validate_obj(self, obj):
        self.validate_str(obj)
        return obj


# This validator is mostly used for documentation, since on Linux
# for example almost anything could be a path
class Path(object):
    def __init__(self):
        pass

    def validate_str(self, s):
        return s

    def validate_obj(self, obj):
        if not isinstance(obj, str):
            raise ValueError
        return obj


class KeyValue(object):
    def __init__(self, key_validator, value_validator):
        self.key_validator = key_validator
        self.value_validator = value_validator

    def validate_str(self, s):
        k, v = s.split("=")
        return (
            self.key_validator.validate_str(k),
            self.value_validator.validate_str(v),
        )

    def validate_obj(self, obj):
        if not isinstance(obj, tuple) or len(obj) != 2:
            raise ValueError
        self.key_validator.validate_obj(obj[0])
        self.value_validator.validate_obj(obj[1])
        return obj


class Dict(object):
    def __init__(self, key_validator, value_validator):
        self.key_validator = key_validator
        self.value_validator = value_validator
        self.list_validator = List(KeyValue(key_validator, value_validator))

    def validate_str(self, s):
        return self.list_validator.validate_str(s)

    def validate_obj(self, obj):
        if not isinstance(obj, dict):
            raise ValueError
        self.list_validator.validate_obj(list(obj.items()))


class Bool(object):
    def __init__(self):
        pass

    def validate_str(self, s):
        if not s in ["true", "false"]:
            raise ValueError
        return s == "true"

    def validate_obj(self, obj):
        if not isinstance(obj, bool):
            raise ValueError
        return obj


class Any(object):
    def __init__(self):
        pass

    def validate_str(self, s):
        return s

    def validate_obj(self, obj):
        return obj
