# Python Idioms Reference

Python 3.14 — this workspace's stack version. Union type syntax `X | Y` requires Python 3.10+.

---

## Section 1 — EAFP over LBYL

**LBYL (Look Before You Leap)** — the anti-pattern:
```python
# Avoid: pre-check before access
if 'key' in data:
    value = data['key']
else:
    value = default

# Avoid: TOCTOU race condition with files
if os.path.exists(path):
    with open(path) as f:  # file could disappear between check and open
        content = f.read()
```

**EAFP (Easier to Ask Forgiveness than Permission)** — the Python idiom:
```python
# Correct: try and handle
try:
    value = data['key']
except KeyError:
    value = default

# Even better for dicts:
value = data.get('key', default)

# Correct: EAFP with files
try:
    with open(path) as f:
        content = f.read()
except FileNotFoundError:
    content = None
```

**Rule:** Use EAFP for dict access, attribute access, file I/O, and type coercion. LBYL
introduces TOCTOU race conditions (check-then-act on external state) and redundant lookups.

---

## Section 2 — Protocol-based duck typing

Use `Protocol` instead of ABC when the interface is structural, not behavioral inheritance.

```python
from typing import Protocol, runtime_checkable

# Define a structural interface — no inheritance required
@runtime_checkable
class Serializable(Protocol):
    def to_dict(self) -> dict: ...

    @classmethod
    def from_dict(cls, data: dict) -> 'Serializable': ...

# Any class with these methods satisfies the Protocol — no import needed
class UserModel:
    def to_dict(self) -> dict:
        return {'id': self.id, 'name': self.name}

    @classmethod
    def from_dict(cls, data: dict) -> 'UserModel':
        return cls(id=data['id'], name=data['name'])

# Type-safe without inheritance:
def save(obj: Serializable) -> None:
    data = obj.to_dict()  # mypy validates this
    ...

# runtime_checkable allows isinstance checks:
assert isinstance(UserModel(), Serializable)  # True
```

**Rule:** Use `Protocol` when callers should not be forced to import and subclass your ABC.
Use ABC when shared implementation (mixin methods) is genuinely needed.

---

## Section 3 — Exception chaining (preserve traceback)

```python
# Anti-pattern: hides original exception and traceback
try:
    result = db.query(sql)
except DatabaseError as e:
    raise AppError("Query failed")  # original traceback LOST

# Correct: preserve original exception
try:
    result = db.query(sql)
except DatabaseError as e:
    raise AppError("Query failed") from e  # chains, preserves traceback

# Explicit suppression (intentional):
try:
    value = cache.get(key)
except CacheError:
    raise CacheMissError(key) from None  # from None = intentional, document why
```

**Rule:** Always use `raise X from e` when re-raising inside an except block. Use `from None`
only when the original error is intentionally suppressed — leave a comment explaining why.

Note: This skill's FastAPI error handling templates (`fastapi-error-handling.md:174,286`)
already use `from exc` consistently. This section is the general rule behind that pattern.

---

## Section 4 — Mutable default argument anti-pattern

```python
# BUG: list/dict default args are shared across ALL calls
def add_item(item: str, items: list[str] = []) -> list[str]:
    items.append(item)  # mutates the shared default!
    return items

add_item('a')  # ['a']
add_item('b')  # ['a', 'b'] — wrong! should be ['b']

# Correct: use None sentinel
def add_item(item: str, items: list[str] | None = None) -> list[str]:
    if items is None:
        items = []
    items.append(item)
    return items

# Same rule for dataclass fields — use field(default_factory=...):
from dataclasses import dataclass, field

@dataclass
class Config:
    tags: list[str] = field(default_factory=list)   # correct
    meta: dict[str, str] = field(default_factory=dict)  # correct
    # tags: list[str] = []  ← WRONG — shared across all Config instances
```

**Rule:** NEVER use mutable objects (`list`, `dict`, `set`) as default argument values.
Use `None` as sentinel for functions; use `field(default_factory=...)` for dataclasses.

---

## Section 5 — `__slots__` (memory-critical classes)

Already covered in `python-advanced-patterns.md` (lines 320–360) with full trade-off analysis.

**Summary rule:** Use `__slots__ = ('x', 'y')` when creating thousands of instances.
Eliminates per-instance `__dict__`, reducing memory ~40–60%. Do NOT use for Pydantic models,
SQLAlchemy ORM models, or general application models.

---

## Section 6 — `isinstance()` vs `type()` equality

```python
# Anti-pattern: type() equality breaks inheritance
def process(obj):
    if type(obj) == int:  # fails for bool (bool is subclass of int)
        ...

# Correct: isinstance() respects inheritance
def process(obj):
    if isinstance(obj, int):  # True for int AND bool
        ...

# isinstance with tuple for multiple types:
if isinstance(value, (int, float)):
    ...

# type() equality is ONLY correct when you explicitly EXCLUDE subclasses:
if type(obj) is int:  # use 'is', not '==' for type comparison
    ...  # intentionally excludes bool — add a comment when you do this
```

**Rule:** Always use `isinstance()` for type checks. Use `type(x) is T` only when you
intentionally need to exclude subclasses, and always document why.

---

## Section 7 — `is None` vs `== None`

```python
# Anti-pattern: == None uses __eq__ which can be overridden by custom classes
if value == None:   # could return True for objects overriding __eq__
    ...

# Correct: is None is an identity check (None is a singleton)
if value is None:
    ...

if value is not None:
    ...

# Same rule for True/False identity checks (when you need strict bool, not truthy):
if flag is True:    # only matches True, not other truthy values
    ...
if flag is False:   # only matches False, not other falsy values
    ...

# For truthiness checks (most common case), plain if/not is correct:
if value:           # truthy check — preferred over == True
    ...
if not value:       # falsy check — preferred over == False
    ...
```

**Rule:** Use `is None` / `is not None` for None checks. Use `== None` nowhere.
Use bare `if value:` for truthiness; use `is True` / `is False` only when strict
bool identity matters (e.g., tristate logic with None/True/False).

---

## Section 8 — Dataclass `__post_init__` for validation

```python
from dataclasses import dataclass, field

@dataclass
class Config:
    host: str
    port: int
    timeout_seconds: float = 30.0
    tags: list[str] = field(default_factory=list)

    def __post_init__(self):
        # Validation runs after the generated __init__ completes
        if not self.host:
            raise ValueError("host cannot be empty")
        if not (1 <= self.port <= 65535):
            raise ValueError(f"Invalid port: {self.port}")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        # Normalize
        self.host = self.host.lower().strip()

# Usage — validation fires automatically:
Config(host='  DB.EXAMPLE.COM  ', port=5432)  # normalized to 'db.example.com'
Config(host='', port=5432)  # raises ValueError immediately
```

**Rule:** Use `__post_init__` for all dataclass validation and normalization. Do NOT add
separate `validate()` methods that callers must remember to call — that is an untested
invariant waiting to be violated.

For API-layer models, prefer Pydantic v2 (`@field_validator`, `model_validator`) — see
`fastapi-templates.md`. Use dataclass `__post_init__` for domain/internal value objects
that must not depend on Pydantic.
