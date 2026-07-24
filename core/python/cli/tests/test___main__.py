"""Tests for cli.__main__ module."""

from unittest.mock import patch

import click

import click

from cli.__main__ import main


def test_main_valid_exits_zero_on_success() -> None:
    with (
        patch("cli.__main__.cli") as mock_cli,
        patch("cli.__main__.sys.exit") as mock_exit,
    ):
        main()
    mock_cli.assert_called_once()
    mock_exit.assert_called_once_with(0)


def test_main_valid_exits_one_on_keyboard_interrupt() -> None:
    with (
        patch("cli.__main__.cli", side_effect=KeyboardInterrupt),
        patch("cli.__main__.click.echo") as mock_echo,
        patch("cli.__main__.sys.exit") as mock_exit,
    ):
        main()
    mock_echo.assert_called_once()
    mock_exit.assert_called_once_with(1)


def test_main_valid_exits_one_on_unexpected_error() -> None:
    with (
        patch("cli.__main__.cli", side_effect=RuntimeError("boom")),
        patch("cli.__main__.click.echo") as mock_echo,
        patch("cli.__main__.sys.exit") as mock_exit,
    ):
        main()
    mock_echo.assert_called_once_with("Error: boom")
    mock_exit.assert_called_once_with(1)
