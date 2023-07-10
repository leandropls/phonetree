from __future__ import annotations

import inspect
from typing import Any, Callable, Iterator, Protocol, Sequence

from rapidfuzz.distance import Indel

__all__ = ["menu", "Ask", "Tell", "Flow"]

Ask = Callable[[str], str | None]

Tell = Callable[[str], None]

ActionCallback = Callable[..., Any]


class NormalizedActionCallback(Protocol):
    def __call__(self, state: Any, ask: Ask, tell: Tell, flow: Flow) -> Any:
        """
        Represents a callback function with a normalized action.

        The method should implement a specific action to be executed given the input state and
        the methods ask and tell. The method should return any object representing the resulting
        state after the action has been taken.

        :param state: The current state of the application or system.
        :param ask: The method to ask questions or make requests to the user.
        :param tell: The method to send messages or information to the user.
        :param flow: The flow object controlling the flow of the application.
        :return: The resulting state after the specific action has been taken.
        """
        ...


def similarity(s1: str, s2: str) -> float:
    """
    Find the normalized Indel similarity between two strings.

    :param s1: The first string to be compared
    :param s2: The second string to be compared
    :return: The normalized Indel similarity value between the two strings,
             ranging from 0.0 (no similarity) to 1.0 (identical strings)
    """
    # Calculate the normalized similarity using the Indel class method
    return Indel.normalized_similarity(s1, s2)


class NextProtocol(Protocol):
    def next(self, state: Any, ask: Ask, tell: Tell) -> tuple[Menu | Action | None, Any]:
        ...


class Flow:
    """Controls the flow of the menu system."""

    __slots__ = ("next",)

    # noinspection PyShadowingBuiltins
    def __init__(self, next: Menu | Action) -> None:
        self.next = next


class Menu(NextProtocol):
    def __init__(
        self,
        parent: Menu | None = None,
        include_exit: bool = False,
        include_exit_on_submenus: bool = False,
    ) -> None:
        """
        Initialize method for the Menu class.

        :param parent: The parent menu object if any, defaults to None
        :param include_exit: Whether to include an Exit option in the menu, defaults to False
        :param include_exit_on_submenus: Whether to include an Exit option in submenus, defaults to False
        """
        self._items: list[tuple[str, Menu | Action]] = []
        self.parent: Menu | None = parent
        self.include_exit: bool = include_exit
        self.include_exit_on_submenus: bool = include_exit_on_submenus
        self.callback: NormalizedActionCallback | None = None

    @property
    def _items_list(self) -> Sequence[tuple[str, Menu | Action | None]]:
        """
        Get the list of menu items including the parent menu and / or Exit option.

        :return: A list containing tuples with menu item names and their corresponding Menu or Action objects
        """
        items: list[tuple[str, Menu | Action | None]] = list(self._items)
        if (parent := self.parent) is not None:
            items.append(("Return to previous menu", parent))
        if parent is None or self.include_exit:
            items.append(("Exit", None))
        return items

    @property
    def _menu(self) -> Iterator[str]:
        """
        Generator function for iterating over the menu item names with their numerical indices.

        :return: An iterator yielding formatted menu item strings
        """
        for i, item in enumerate(self._items_list):
            yield f"{i + 1}. {item[0]}"

    def _get_item(self, name: str) -> Menu | Action | None:
        """
        Get the Menu or Action object corresponding to a user's input.

        :param name: The user's input
        :return: The Menu or Action object associated with the user's input, or raise KeyError if not found
        """
        # Find the object with the closest text similarity to the input name
        max_ratio, item = max((similarity(x[0].lower(), name.lower()), x) for x in self._items_list)
        if max_ratio >= 0.5:
            return item[1]

        # Find the object by its index in the menu
        max_ratio, index = max(
            (similarity(str(i), name), i) for i, _ in enumerate(self._items_list, 1)
        )
        if max_ratio >= 0.5:
            return self._items_list[index - 1][1]

        raise KeyError(name)

    def __call__(self, callback: ActionCallback) -> Menu:
        """
        Set the callback function for the menu.

        :param callback: The callback function to be called when the menu is opened
        :return: The menu object itself for method chaining
        """
        self.callback = normalize_callback(callback) if callback is not None else None
        return self

    def menu(
        self,
        name: str,
        include_exit: bool | None = None,
        include_exit_on_submenus: bool | None = None,
    ) -> Menu:
        """
        Add a submenu to the current menu.

        :param name: The name of the submenu
        :param include_exit: Whether to include an Exit option in the submenu,
            defaults to self.include_exit_on_submenus
        :param include_exit_on_submenus: Whether to include an Exit option in submenus,
            defaults to self.include_exit_on_submenus
        :return: The submenu object
        """
        submenu = Menu(
            parent=self,
            include_exit=include_exit
            if include_exit is not None
            else self.include_exit_on_submenus,
            include_exit_on_submenus=include_exit_on_submenus
            if include_exit_on_submenus is not None
            else self.include_exit_on_submenus,
        )
        self._items.append((name, submenu))
        return submenu

    def action(
        self,
        name: str,
    ) -> Action:
        """
        Add an action to the current menu.

        :param name: The name of the action
        :return: The action object
        """
        action = Action(parent=self)
        self._items.append((name, action))
        return action

    def next(
        self,
        state: Any,
        ask: Ask,
        tell: Tell,
    ) -> tuple[Menu | Action | None, Any]:
        """
        Get the next menu action or menu object based on the user's input.

        :param state: The state object from previous interaction
        :param ask: The `ask` function for getting user input
        :param tell: The `tell` function for providing information to the user
        :return: A tuple with the next Menu or Action object and the updated state
        """
        # Trigger the callback if it's set
        if (callback := self.callback) is not None:
            state = callback(state, ask, tell, Flow(self))

        # Display the menu options to the user
        question = "Please select an option:\n" + "\n".join(self._menu)

        while True:
            question_answer = ask(question)

            # If answer is None, the user has exited the program
            if question_answer is None:
                return None, state

            try:
                return self._get_item(question_answer), state
            except KeyError:
                question = "Invalid option, please try again."

    def communicate(self, state: Any, ask: Ask, tell: Tell) -> None:
        """
        Primary method for communication with the user in the menu-based system.

        :param state: An object representing the state of the conversation
        :param ask: The `ask` function for getting user input
        :param tell: The `tell` function for providing information to the user
        """
        current: Menu | Action | None = self
        while current is not None:
            current, state = current.next(state, ask, tell)


def menu(
    include_exit: bool = False,
    include_exit_on_submenus: bool = False,
) -> Menu:
    """
    Create a new menu.

    :param include_exit: Whether to include an Exit option in the menu, defaults to False
    :param include_exit_on_submenus: Whether to include an Exit option in submenus, defaults to False
    """
    return Menu(include_exit=include_exit, include_exit_on_submenus=include_exit_on_submenus)


class Action(NextProtocol):
    def __init__(
        self,
        parent: Menu,
    ) -> None:
        """
        Initializes the Action object.

        :param parent: The parent menu of this action.
        """
        self.parent = parent
        self.callback: NormalizedActionCallback | None = None

    def next(
        self,
        state: Any,
        ask: Ask,
        tell: Tell,
    ) -> tuple[Menu | Action, Any]:
        """
        Executes the action callback and provides a next menu and updated state.

        :param state: The current state of the menu system.
        :param ask: An instance of the Ask object used for questions to the user.
        :param tell: An instance of the Tell object used to communicate information to
            the user.
        :return: A tuple containing the next menu object and the updated state.
        """
        flow = Flow(self.parent)
        if (callback := self.callback) is not None:
            state = callback(state, ask=ask, tell=tell, flow=flow)
        return flow.next, state

    def __call__(self, callback: ActionCallback) -> Action:
        """
        Sets the action callback for this action.

        :param callback: The function to be called during action execution.
        :return: The updated action with the new callback.
        """
        # Normalize the callback if it is not None, otherwise set it to None
        self.callback = normalize_callback(callback) if callback is not None else None
        return self


def normalize_callback(callback: ActionCallback) -> NormalizedActionCallback:
    """
    Normalize a given callback function to have `state`, `ask`, `tell`, and `flow` as arguments. The
    given callback may have only `state` as positional argument and `ask`, `tell` and `action` as keyword arguments.

    :param callback: The callback function to normalize.
    :return: The normalized callback function, accepting `state`, `ask`, `tell`, and 'action' as arguments.
    :raises ValueError: If the given callback function has unsupported number of arguments or
        an invalid signature.
    """
    signature = inspect.signature(callback)
    parameters = signature.parameters
    kwargs = []

    params = list(parameters.keys())

    if len(params) > 0 and params[0] not in ("ask", "tell", "flow"):
        params.pop(0)
        hasState = True
    else:
        hasState = False

    while params:
        param = params.pop(0)
        if param not in ("ask", "tell", "flow"):
            raise ValueError("Unsupported argument in callback function: {}".format(param))
        kwargs.append(param)

    def normalized_callback(state: Any, ask: Ask, tell: Tell, flow: Flow) -> Any:
        callbackLocals = locals()
        return callback(
            *((state,) if hasState else ()),
            **{k: callbackLocals[k] for k in kwargs},
        )

    normalized_callback.__name__ = callback.__name__
    normalized_callback.__doc__ = callback.__doc__

    return normalized_callback
