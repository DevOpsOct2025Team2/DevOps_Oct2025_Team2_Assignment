from app import create_app


def test_health_endpoint_returns_status_and_version():
    app = create_app("testing")
    client = app.test_client()

    response = client.get("/health")

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_api_blueprint_is_registered():
    app = create_app("testing")
    routes = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/api/v1/auth/login" in routes
    assert "/api/v1/admin/users" in routes
