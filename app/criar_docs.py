from pathlib import Path

DOCS = {
    "kpis.md": """
# Documento fictício para estudo: definições de KPI do PCP

## OTD - Entrega no prazo
O OTD (On-Time Delivery) mede a proporção de ordens de produção concluídas até a data de vencimento.
Fórmula: ordens com date(EndDate) <= date(DueDate), divididas pelo total de ordens da tabela WorkOrder.
Meta: OTD maior ou igual a 90%.
Classificação: abaixo de 90% é alerta amarelo. Abaixo de 80% é alerta vermelho.

## Taxa de refugo
A taxa de refugo mede a parcela da quantidade produzida que foi descartada.
Fórmula: SUM(ScrappedQty) dividido por SUM(OrderQty) na tabela WorkOrder.
Meta: taxa de refugo menor ou igual a 1,0%. Acima de 2,0% exige análise de causa raiz.

## Taxa de recebimento completo
A taxa de recebimento completo mede quantas linhas de compra chegaram inteiras.
Fórmula: linhas de PurchaseOrderDetail com ReceivedQty >= OrderQty, divididas pelo total de linhas.
Meta: maior ou igual a 95%.

## Lead time real de produção
É o número de dias entre StartDate e EndDate de cada ordem. Use julianday(EndDate) - julianday(StartDate).
Este indicador não tem meta formal. É usado para acompanhar tendência.
""",
    "politica_compras.md": """
# Documento fictício para estudo: política de compras e recebimento

## Recebimento parcial
Quando o fornecedor entrega menos do que o pedido (ReceivedQty menor que OrderQty), o comprador registra o saldo como pendente.
O comprador cobra o fornecedor em até 2 dias úteis.
Se o saldo pendente for maior que 20% da quantidade pedida, o item entra na lista de risco de abastecimento.

## Fornecedor com baixo desempenho
O fornecedor com taxa de recebimento completo abaixo de 90% por dois trimestres seguidos entra em plano de ação.
O plano de ação é revisado pelo comprador responsável e pelo gerente de supply chain.

## Aprovações
Mudança de estoque de segurança (SafetyStockLevel) exige aprovação do gerente de supply chain.
Compras emergenciais também exigem aprovação do gerente de supply chain.
""",
    "glossario_pcp.md": """
# Documento fictício para estudo: glossário de PCP

## MRP
MRP (Material Requirements Planning) calcula quanto material comprar ou produzir, e quando, a partir da demanda e da lista de materiais.

## Lista de materiais (BOM)
A lista de materiais (BOM, tabela BillOfMaterials) diz quais componentes e quantidades formam cada produto montado.

## Estoque de segurança
O estoque de segurança (SafetyStockLevel) é a quantidade mantida acima da demanda esperada para absorver variações de demanda e de prazo de entrega.

## Ponto de reposição
O ponto de reposição (ReorderPoint) é o nível de estoque em que um novo pedido deve ser disparado.

## Ordem de produção
A ordem de produção (OP, tabela WorkOrder) autoriza a fabricação de uma quantidade de um produto, com data de início, data de fim e data de vencimento.
""",
}


def main():
    pasta = Path("docs")
    pasta.mkdir(exist_ok=True)
    for nome, texto in DOCS.items():
        destino = pasta / nome
        if destino.exists():
            print("já existe, mantido:", destino)
            continue
        destino.write_text(texto.strip() + "\n", encoding="utf-8")
        print("criado:", destino)


if __name__ == "__main__":
    main()