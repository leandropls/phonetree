from __future__ import annotations

import inspect
from typing import Any, Callable, Iterator, Protocol, Sequence

from rapidfuzz.distance import Indel

__all__ = ["menu", "Ask", "Tell"]

Ask = Callable[[str], str]

Tell = Callable[[str], None]

ActionCallback = Callable[..., Any]


class NormalizedActionCallback(Protocol):
    def __call__(self, state: Any, ask: Ask, tell: Tell) -> Any:
        ...


def similarity(s1: str, s2: str) -> float:
    """Find the normalized Indel similarity between two strings"""
    return Indel.normalized_similarity(s1, s2)


class NextProtocol(Protocol):
    def next(self, state: Any, ask: Ask, tell: Tell) -> tuple[Menu | Action | None, Any]:
        ...


class Menu(NextProtocol):
    def __init__(
        self,
        parent: Menu | None = None,
    ) -> None:
        self._items: list[tuple[str, Menu | Action]] = []
        self.parent: Menu | None = parent
        self.callback: NormalizedActionCallback | None = None

    @property
    def _items_list(self) -> Sequence[tuple[str, Menu | Action | None]]:
        items: list[tuple[str, Menu | Action | None]] = list(self._items)
        if (parent := self.parent) is not None:
            items.append(("Return to previous menu", parent))
        else:
            items.append(("Exit", None))
        return items

    @property
    def _menu(self) -> Iterator[str]:
        for i, item in enumerate(self._items_list):
            yield f"{i + 1}. {item[0]}"

    def _get_item(self, name: str) -> Menu | Action | None:
        max_ratio, item = max((similarity(x[0].lower(), name.lower()), x) for x in self._items_list)
        if max_ratio >= 0.5:
            return item[1]

        max_ratio, index = max(
            (similarity(str(i), name), i) for i, _ in enumerate(self._items_list, 1)
        )
        if max_ratio >= 0.5:
            return self._items_list[index - 1][1]

        raise KeyError(name)

    def __call__(self, callback: ActionCallback) -> Menu:
        self.callback = normalize_callback(callback) if callback is not None else None
        return self

    def menu(self, name: str) -> Menu:
        submenu = Menu(parent=self)
        self._items.append((name, submenu))
        return submenu

    def action(
        self,
        name: str,
    ) -> Action:
        action = Action(parent=self)
        self._items.append((name, action))
        return action

    def next(
        self,
        state: Any,
        ask: Ask,
        tell: Tell,
    ) -> tuple[Menu | Action | None, Any]:
        if (callback := self.callback) is not None:
            state = callback(state, ask, tell)
        question = "Please select an option:\n" + "\n".join(self._menu)
        while True:
            question_answer = ask(question)
            try:
                return self._get_item(question_answer), state
            except KeyError:
                question = "Invalid option, please try again."

    def communicate(self, state: Any, ask: Ask, tell: Tell) -> None:
        current: Menu | Action | None = self
        while current is not None:
            current, state = current.next(state, ask, tell)


def menu() -> Menu:
    return Menu()


class Action(NextProtocol):
    def __init__(
        self,
        parent: Menu,
    ) -> None:
        self.parent = parent
        self.callback: NormalizedActionCallback | None = None

    def next(
        self,
        state: Any,
        ask: Ask,
        tell: Tell,
    ) -> tuple[Menu, Any]:
        if (callback := self.callback) is not None:
            state = callback(state, ask=ask, tell=tell)
        return self.parent, state

    def __call__(self, callback: ActionCallback) -> Action:
        self.callback = normalize_callback(callback) if callback is not None else None
        return self


def normalize_callback(callback: ActionCallback) -> NormalizedActionCallback:
    signature = inspect.signature(callback)
    parameters = signature.parameters
    if len(parameters) == 3:
        # def callback(state: Any, ask: Ask, tell: Tell) -> Any:
        return callback
    elif len(parameters) == 2:
        if "ask" in parameters and "tell" not in parameters:
            # def callback(state: Any, ask: Ask) -> Any:
            return lambda state, ask, tell: callback(state, ask=ask)
        elif "ask" not in parameters and "tell" in parameters:
            # def callback(state: Any, tell: Tell) -> Any:
            return lambda state, ask, tell: callback(state, tell=tell)
        elif "ask" in parameters and "tell" in parameters:
            # def callback(ask: Ask, tell: Tell) -> Any:
            return lambda state, ask, tell: callback(ask=ask, tell=tell)
        else:
            raise ValueError("wrong callback signature")
    elif len(parameters) == 1:
        if "ask" in parameters:
            # def callback(ask: Ask) -> Any:
            return lambda state, ask, tell: callback(ask=ask)
        elif "tell" in parameters:
            # def callback(tell: Tell) -> Any:
            return lambda state, ask, tell: callback(tell=tell)
        else:
            # def callback(state: Any) -> Any:
            return lambda state, ask, tell: callback(state)
    elif len(parameters) == 0:
        # def callback() -> Any:
        return lambda state, ask, tell: callback()
    else:
        raise ValueError("wrong callback signature")
