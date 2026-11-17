from tests.ayudantes import cuerpo_pedido


def test_compra_descuenta_stock(client, cliente, producto):
    r = client.post(
        "/pedidos", headers=cliente, json=cuerpo_pedido(producto["id"], 1)
    )
    assert r.status_code == 201
    prod_actualizado = client.get(f"/productos/{producto['id']}").json()
    assert prod_actualizado["stock"] == 1


def test_sin_stock_da_409_y_no_toca_nada(client, cliente, producto):
    r = client.post(
        "/pedidos", headers=cliente, json=cuerpo_pedido(producto["id"], 3)
    )
    assert r.status_code == 409
    assert client.get(f"/productos/{producto['id']}").json()["stock"] == 2
    assert client.get("/pedidos/mios", headers=cliente).json() == []


def test_precio_congelado(client, cliente, admin, producto):
    r_compra = client.post(
        "/pedidos", headers=cliente, json=cuerpo_pedido(producto["id"], 1)
    )
    assert r_compra.status_code == 201

    client.put(
        f"/productos/{producto['id']}",
        headers=admin,
        json={
            "nombre": producto["nombre"],
            "descripcion": producto["descripcion"],
            "precio": 9999,
        },
    )

    historial = client.get("/pedidos/mios", headers=cliente).json()
    assert len(historial) == 1
    pedido = historial[0]
    precio_guardado = pedido.get("precio_unitario") or pedido.get("total")
    assert precio_guardado == 1000


def test_comprar_sin_sesion_da_401(client, producto):
    r = client.post("/pedidos", json=cuerpo_pedido(producto["id"], 1))
    assert r.status_code == 401