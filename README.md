# PhoneTree

PhoneTree is a Python framework for creating text-based menu systems, resembling phone tree systems or rudimentary chatbots. It allows you to easily create menus and actions, manage user input and output, and maintain state between interactions.

## Features

- Simple decorator-based syntax for defining menus and actions
- Optional "ask" and "tell" callbacks for handling user input and output
- State management for passing data between menus and actions

## Installation

To install PhoneTree, simply use pip:

```
pip install phonetree
```

## Usage

Here's an example of how to use PhoneTree to create a simple menu system:

```python
import phonetree
from phonetree import Ask, Tell

@phonetree.menu()
def main_menu(state: dict) -> dict:
    """Main menu."""
    return {"interactions": state.get("interactions", 0) + 1}

@main_menu.menu("First Submenu")
def first_submenu(state: dict) -> dict:
    """First Submenu menu."""
    # here goes the code that runs when you enter the submenu
    ...

    return {"interactions": state.get("interactions", 0) + 1}

@first_submenu.action("Do something")
def do_something(state: dict, ask: Ask, tell: Tell) -> dict:
    """Some action"""
    anything = ask("Is there anything you want to say?")
    print("user answered: " + anything)
    tell("Alright! Thank you!")
    return {"interactions": state.get("interactions", 0) + 1}

@first_submenu.action("Do something else")
def do_something_else(state: dict, ask: Ask, tell: Tell) -> dict:
    """Some action"""
    color = ask("What's your favorite color?")
    print("User said " + color + " is their favorite color.")
    tell("Alright! Nice to know!")
    return {"interactions": state.get("interactions", 0) + 1, "favorite_color": color}

@main_menu.menu("Second submenu")
def second_submenu(state: dict, tell: Tell) -> dict:
    """Second submenu."""
    tell("Welcome to second submenu!")
    return {"interactions": state.get("interactions", 0) + 1}
```

### Defining Menus and Actions

To define a menu, simply use the `@phonetree.menu()` decorator on a function. The function should return a dictionary representing the new state of the menu. This state will be passed on to the next menu or action function call.

To define an action within a menu, use the `@menu.action("Action Name")` decorator on a function. The function should also return a dictionary representing the new state of the menu.

### Handling User Input and Output

Menu and action functions can take optional "ask" and "tell" callbacks.

The "ask" function sends some text to the user and expects an answer, returning the answer as the response of the function call. If the function returns `None`, the program execution is ended.

The "tell" function just sends some text to the user and doesn't return anything back. Both functions are recognized by their names in the menu/action functions argument list.

### State Management

Menu and action functions can also take a state variable, which can be called anything (except for "ask" and "tell"). This argument is optional, but if passed, should be the first argument of the function. This argument can receive a state of any type.

The function should return the new state of the menu, which will determine what will be passed on as the state for the next menu/action function call. This state can be any object, including `None`, if the user doesn't need to keep any state.

### Running the Application

To run the application defined by the menu, call the `communicate` method for the menu, passing the state, ask, and tell callbacks:

```python
# communicate(state, ask, tell)
main_menu.communicate({"interactions": 0}, input, print)
```

This will start the menu system and handle user interactions according to the defined menu and action functions.


## License

PhoneTree is released under the MIT License.
