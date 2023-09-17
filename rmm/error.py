import typing as t


class Result:
    def __init__(self, is_err: bool, value: t.Any):
        self.is_err = is_err
        self.value = value

    def is_error(self) -> bool:
        return self.is_err

    def unwrap(self) -> t.Any:
        if self.is_err:
            raise TypeError(f"Error: {self.value}")
        return self.value

    def unwrap_or(self, value: t.Any) -> t.Any:
        if self.is_err:
            return value
        return self.value

    def __str__(self):
        return f"Result({self.is_err}, {self.value})"

    __repr__ = __str__


class Ok(Result):
    def __init__(self, value):
        super().__init__(False, value)


class Err(Result):
    def __init__(self, error):
        super().__init__(True, error)
