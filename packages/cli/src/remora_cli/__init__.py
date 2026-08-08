def run() -> None:
    from remora_cli.commands import create_app

    app = create_app()
    app()
