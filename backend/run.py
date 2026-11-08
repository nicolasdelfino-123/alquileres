from app import create_app

app = create_app()

if __name__ == "__main__":
    if app.config["PRODUCTION"]:
        raise RuntimeError("En producción usar Gunicorn; consultar PRODUCTION.md")
    from flask_migrate import upgrade
    with app.app_context():
        upgrade()
        from app.initial_admin import ensure_local_admin
        ensure_local_admin()
    app.run(debug=False)
