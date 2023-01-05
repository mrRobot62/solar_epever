# SPDX-FileCopyrightText: Copyright (c) 2021 Dan Halbert for Adafruit Industries LLC
# SPDX-FileCopyrightText: 2021 James Carr
#
# SPDX-License-Identifier: MIT
"""
`adafruit_simplemath`
================================================================================

Math utility functions


* Author(s): Dan Halbert, James Carr

Implementation Notes
--------------------

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://github.com/adafruit/circuitpython/releases
"""

__version__ = "2.0.8"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_SimpleMath.git"


def map_range(
    x: float, in_min: float, in_max: float, out_min: float, out_max: float
) -> float:
    """
    Maps a number from one range to another. Somewhat similar to the Arduino
    :attr:`map()` function, but returns a floating point result, and
    constrains the output value to be between :attr:`out_min` and
    :attr:`out_max`. If :attr:`in_min` is greater than :attr:`in_max` or
    :attr:`out_min` is greater than :attr:`out_max`, the corresponding range
    is reversed, allowing, for example, mapping a range of 0-10 to 50-0.

    See also :py:func:`map_unconstrained_range`

    .. code-block::

        from adafruit_simplemath import map_range

        percent = 23
        screen_width = 320  # or board.DISPLAY.width
        x = map_range(percent, 0, 100, 0, screen_width - 1)
        print("X position", percent, "% from the left of screen is", x)

    :param float x: Value to convert
    :param float in_min: Start value of input range.
    :param float in_max: End value of input range.
    :param float out_min: Start value of output range.
    :param float out_max: End value of output range.
    :return: Returns value mapped to new range.
    :rtype: float
    """

    mapped = map_unconstrained_range(x, in_min, in_max, out_min, out_max)
    return constrain(mapped, out_min, out_max)


def map_unconstrained_range(
    x: float, in_min: float, in_max: float, out_min: float, out_max: float
) -> float:
    """
    Maps a number from one range to another. Somewhat similar to the Arduino
    :attr:`map()` function, but returns a floating point result, and
    does not constrain the output value to be between :attr:`out_min` and
    :attr:`out_max`. If :attr:`in_min` is greater than :attr:`in_max` or
    :attr:`out_min` is greater than :attr:`out_max`, the corresponding range
    is reversed, allowing, for example, mapping a range of 0-10 to 50-0.

    See also :py:func:`map_range`

    .. code-block::

        from adafruit_simplemath import map_unconstrained_range

        celsius = -20
        fahrenheit = map_unconstrained_range(celsius, 0, 100, 32, 212)
        print(celsius, "degress Celsius =", fahrenheit, "degrees Fahrenheit")

    :param float x: Value to convert
    :param float in_min: Start value of input range.
    :param float in_max: End value of input range.
    :param float out_min: Start value of output range.
    :param float out_max: End value of output range.
    :return: Returns value mapped to new range.
    :rtype: float
    """
    in_range = in_max - in_min
    in_delta = x - in_min
    if in_range != 0:
        mapped = in_delta / in_range
    elif in_delta != 0:
        mapped = in_delta
    else:
        mapped = 0.5
    mapped *= out_max - out_min
    mapped += out_min

    return mapped


def constrain(x: float, out_min: float, out_max: float) -> float:
    """Constrains :attr:`x` to be within the inclusive range
    [:attr:`out_min`, :attr:`out_max`]. Sometimes called :attr:`clip` or
    :attr:`clamp` in other libraries. :attr:`out_min` should be less than or
    equal to :attr:`out_max`.
    If :attr:`x` is less than :attr:`out_min`, return :attr:`out_min`.
    If :attr:`x` is greater than :attr:`out_max`, return :attr:`out_max`.
    Otherwise just return :attr:`x`.
    If :attr:`max_value` is less than :attr:`min_value`, they will be swapped.

    :param float x: Value to constrain
    :param float out_min: Lower bound of output range.
    :param float out_max: Upper bound of output range.
    :return: Returns value constrained to given range.
    :rtype: float
    """
    if out_min <= out_max:
        return max(min(x, out_max), out_min)
    return min(max(x, out_max), out_min)
