def run() -> None:
    from remora_cli.commands.main import create_app

    app = create_app()
    app()
