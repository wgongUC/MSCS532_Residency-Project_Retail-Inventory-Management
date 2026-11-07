"""AVL tree indexed by (integer price cents, SKU)."""
from dataclasses import dataclass
from typing import Iterator

Key = tuple[int, str]


@dataclass
class Node:
    key: Key
    left: 'Node | None' = None
    right: 'Node | None' = None
    height: int = 1


def _height(n: Node | None) -> int:
    return n.height if n else 0


def _refresh(n: Node) -> None:
    n.height = 1 + max(_height(n.left), _height(n.right))


def _right(y: Node) -> Node:
    x = y.left
    assert x is not None
    y.left, x.right = x.right, y
    _refresh(y)
    _refresh(x)
    return x


def _left(x: Node) -> Node:
    y = x.right
    assert y is not None
    x.right, y.left = y.left, x
    _refresh(x)
    _refresh(y)
    return y


def _balance(n: Node) -> Node:
    _refresh(n)
    diff = _height(n.left) - _height(n.right)
    if diff > 1:
        assert n.left
        if _height(n.left.left) < _height(n.left.right):
            n.left = _left(n.left)
        return _right(n)
    if diff < -1:
        assert n.right
        if _height(n.right.right) < _height(n.right.left):
            n.right = _right(n.right)
        return _left(n)
    return n


def _insert(root: Node | None, key: Key) -> Node:
    if root is None:
        return Node(key)
    if key < root.key:
        root.left = _insert(root.left, key)
    elif key > root.key:
        root.right = _insert(root.right, key)
    else:
        raise ValueError('Duplicate AVL key')
    return _balance(root)


def _min(root: Node) -> Node:
    while root.left:
        root = root.left
    return root


def _remove(root: Node | None, key: Key) -> Node | None:
    if root is None:
        raise KeyError(f'Missing AVL key: {key}')
    if key < root.key:
        root.left = _remove(root.left, key)
    elif key > root.key:
        root.right = _remove(root.right, key)
    else:
        if not root.left:
            return root.right
        if not root.right:
            return root.left
        successor = _min(root.right)
        root.key = successor.key
        root.right = _remove(root.right, successor.key)
    return _balance(root)


class AVLPriceTree:
    def __init__(self):
        self.root: Node | None = None

    def insert(self, key: Key) -> None:
        self.root = _insert(self.root, key)

    def remove(self, key: Key) -> None:
        self.root = _remove(self.root, key)

    def sorted_keys(self) -> Iterator[Key]:
        def walk(n: Node | None) -> Iterator[Key]:
            if n:
                yield from walk(n.left)
                yield n.key
                yield from walk(n.right)
        return walk(self.root)

    def between(self, low: int, high: int) -> Iterator[Key]:
        """Pruned in-order traversal: O(log n + k) on AVL tree."""
        def walk(n: Node | None) -> Iterator[Key]:
            if n is None:
                return
            price = n.key[0]
            if price >= low:
                yield from walk(n.left)
            if low <= price <= high:
                yield n.key
            if price <= high:
                yield from walk(n.right)
        return walk(self.root)

    def validate(self) -> None:
        def visit(n: Node | None, lo: Key | None, hi: Key | None) -> int:
            if not n:
                return 0
            assert lo is None or lo < n.key
            assert hi is None or n.key < hi
            lh = visit(n.left, lo, n.key)
            rh = visit(n.right, n.key, hi)
            assert abs(lh - rh) <= 1, ('unbalanced', n.key)
            assert n.height == max(lh, rh) + 1
            return n.height
        visit(self.root, None, None)
