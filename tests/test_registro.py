def test_registro_sin_consentimiento_se_rechaza(client):
    r = client.post(
        "/auth/register",
        json={
            "nombre": "Sin Permiso",
            "email": "sinpermiso@prueba.com",
            "password": "clave-larga-123",
            "acepto_tratamiento": False,
        },
    )
    assert r.status_code == 422


def test_registro_con_consentimiento_y_login(client):
    r = client.post(
        "/auth/register",
        json={
            "nombre": "Usuario Valido",
            "email": "valido@prueba.com",
            "password": "clave-larga-123",
            "acepto_tratamiento": True,
        },
    )
    assert r.status_code == 201
    datos = r.json()
    assert "password" not in datos
    assert "hashed_password" not in datos

    r_login = client.post(
        "/auth/login",
        data={"username": "valido@prueba.com", "password": "clave-larga-123"},
    )
    assert r_login.status_code == 200
    assert "access_token" in r_login.json()


def test_login_con_clave_incorrecta(client):
    client.post(
        "/auth/register",
        json={
            "nombre": "Usuario Clave",
            "email": "clave@prueba.com",
            "password": "clave-larga-123",
            "acepto_tratamiento": True,
        },
    )
    r = client.post(
        "/auth/login",
        data={"username": "clave@prueba.com", "password": "clave-incorrecta"},
    )
    assert r.status_code == 401