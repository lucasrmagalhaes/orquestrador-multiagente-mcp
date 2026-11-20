from orquestrador.politica import avaliar_ferramenta


def test_leitura_da_agenda_passa():
    decisao = avaliar_ferramenta("agenda", "listar_compromissos", 0)
    assert decisao.permitido


def test_exfiltracao_nao_passa():
    decisao = avaliar_ferramenta("notas", "exfiltrate_secrets", 0)
    assert not decisao.permitido
    assert decisao.motivo == "ferramenta proibida"


def test_agente_nao_usa_ferramenta_de_outro():
    decisao = avaliar_ferramenta("agenda", "buscar_notas", 0)
    assert not decisao.permitido
