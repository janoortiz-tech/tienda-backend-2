from tests.ayudantes import cuerpo_pedido


def test_arrepentimiento_sin_sesion(client, cliente, producto):
    r_compra = client.post(
        "/pedidos", headers=cliente, json=cuerpo_pedido(producto["id"], 1)
    )
    assert r_compra.status_code == 201
    pedido_id = r_compra.json()["id"]

    r_arr = client.post(
        "/arrepentimiento",
        json={"pedido_id": pedido_id, "email": "cliente@prueba.com"},
    )
    assert r_arr.status_code == 201
    assert "codigo" in r_arr.json() or "mensaje" in r_arr.json()
    assert client.get(f"/productos/{producto['id']}").json()["stock"] == 2


def test_arrepentimiento_no_revela(client):
    r = client.post(
        "/arrepentimiento",
        json={"pedido_id": 99999, "email": "nadie@prueba.com"},
    )
    assert r.status_code == 201
    assert "codigo" in r.json() or "mensaje" in r.json()