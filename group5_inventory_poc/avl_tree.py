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
    # PERF fix 2: this runs on every node of every insert/remove path.
    # The original called _refresh() (which calls _height() twice and max())
    # and then _height() twice more: about 6 function calls per node. Read each
    # child height once, inline, and leave right away in the common case
    # where the node is still balanced. Rotations below are unchanged, so the
    # resulting tree is identical.
    left, right = n.left, n.right
    lh = left.height if left is not None else 0
    rh = right.height if right is not None else 0
    n.height = (lh if lh > rh else rh) + 1
    diff = lh - rh
    if -1 <= diff <= 1:
        return n
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

    # PERF fix 1: iterative traversals.
    # The original versions were recursive generators chained with
    # "yield from". Each yielded key then travels back up through EVERY
    # ancestor generator frame (about log n of them), and a generator is
    # created even for empty children. That made a range query cost
    # O(k log n) in practice, not O(log n + k). One explicit stack and one
    # generator frame give real O(log n + k), with the same visit order and
    # the same output.

    def sorted_keys(self) -> Iterator[Key]:
        stack: list[Node] = []
        n = self.root
        while stack or n is not None:
            while n is not None:          # go as far left as possible
                stack.append(n)
                n = n.left
            n = stack.pop()
            yield n.key
            n = n.right

    def between(self, low: int, high: int) -> Iterator[Key]:
        """Pruned in-order traversal: O(log n + k) on AVL tree."""
        stack: list[Node] = []
        n = self.root
        while stack or n is not None:
            if n is not None:
                if n.key[0] < low:
                    n = n.right           # node and its left subtree are below the range
                else:
                    stack.append(n)       # may be in range: visit left side first
                    n = n.left
                continue
            n = stack.pop()
            if n.key[0] > high:
                return                    # every later key is larger: stop
            yield n.key
            n = n.right

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
