from flask import abort

from app import create_app


def _build_client():
    app = create_app("testing")
    app.config["TESTING"] = False
    app.config["PROPAGATE_EXCEPTIONS"] = False

    @app.route("/raise-http")
    def raise_http():
        abort(400, description="bad request payload")

    @app.route("/raise-generic")
    def raise_generic():
        raise ValueError("unexpected failure")

    return app.test_client()


def test_http_exception_handler_returns_json_payload():
    client = _build_client()
    response = client.get("/raise-http")

    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "Bad Request"
    assert data["message"] == "bad request payload"


def test_generic_exception_handler_returns_500_json_payload():
    client = _build_client()
    response = client.get("/raise-generic")

    assert response.status_code == 500
    data = response.get_json()
    assert data["error"] == "Internal Server Error"
    assert data["message"] == "Unexpected error."
