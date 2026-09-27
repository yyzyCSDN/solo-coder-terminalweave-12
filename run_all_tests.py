import contextlib
import importlib.util
import sys
import traceback
import types
from pathlib import Path

pytest = types.ModuleType("pytest")

class _Raises:
    def __init__(self, exc):
        self.exc = exc
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            raise AssertionError(f"expected {self.exc.__name__} but nothing raised")
        return issubclass(exc_type, self.exc)

def raises(exc, *a, **k):
    return _Raises(exc)

def fixture(*dargs, **dkw):
    if dargs and callable(dargs[0]):
        @contextlib.contextmanager
        def wrap(*a, **k):
            yield dargs[0](*a, **k)
        wrap.__name__ = dargs[0].__name__
        return wrap
    def deco(fn):
        @contextlib.contextmanager
        def wrap(*a, **k):
            gen = fn(*a, **k)
            yield next(gen)
            with contextlib.suppress(StopIteration):
                next(gen)
        wrap.__name__ = fn.__name__
        return wrap
    return deco

class _Mark:
    def __getattr__(self, name):
        def deco(fn=None, *a, **k):
            if fn is None:
                return lambda f: f
            return fn
        return deco
    parametrize = lambda *a, **k: (lambda fn: fn)

class _Approx(float):
    def __new__(cls, expected, rel=None, abs=None):
        obj = float.__new__(cls, expected)
        obj.rel = 1e-6 if rel is None else rel
        obj.abs = 1e-12 if abs is None else abs
        return obj
    def __eq__(self, other):
        return abs(float(self) - float(other)) <= max(self.abs, self.rel * abs(float(self)))

def approx(expected, rel=None, abs=None):
    return _Approx(expected, rel, abs)

pytest.approx = approx
pytest.raises = raises
pytest.fixture = fixture
pytest.mark = _Mark()
pytest.skip = lambda *a, **k: None
sys.modules["pytest"] = pytest

failed = 0
for arg in sys.argv[1:]:
    path = Path(arg)
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for name in sorted(dir(mod)):
        if not name.startswith("test_"):
            continue
        fn = getattr(mod, name)
        try:
            sig = fn.__code__.co_varnames[: fn.__code__.co_argcount]
            kwargs = {}
            for pname in sig:
                fix = getattr(mod, pname, None)
                if fix is not None and hasattr(fix, "__enter__"):
                    cm = fix()
                    kwargs[pname] = cm.__enter__()
                else:
                    raise AssertionError(f"no fixture {pname}")
            fn(**kwargs)
            for cm in getattr(fn, "_cms", []):
                pass
            print(f"PASS {path.name}::{name}")
        except Exception:
            failed += 1
            print(f"FAIL {path.name}::{name}")
            traceback.print_exc()

print(f"\n{failed} failure(s)")
sys.exit(1 if failed else 0)
