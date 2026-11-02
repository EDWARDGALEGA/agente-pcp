# Documento fictício para estudo: definições de KPI do PCP

## OTD - Entrega no prazo
O OTD (On-Time Delivery) mede a proporção de ordens de produção concluídas até a data de vencimento.
Fórmula: ordens com date(EndDate) <= date(DueDate), divididas pelo total de ordens da tabela WorkOrder.
Meta: OTD maior ou igual a 90%.
Classificação: abaixo de 90% é alerta amarelo. Abaixo de 85% é alerta vermelho.

## Taxa de refugo
A taxa de refugo mede a parcela da quantidade produzida que foi descartada.
Fórmula: SUM(ScrappedQty) dividido por SUM(OrderQty) na tabela WorkOrder.
Meta: taxa de refugo menor ou igual a 1,0%. Acima de 3% exige análise de causa raiz.

## Taxa de recebimento completo
A taxa de recebimento completo mede quantas linhas de compra chegaram inteiras.
Fórmula: linhas de PurchaseOrderDetail com ReceivedQty >= OrderQty, divididas pelo total de linhas.
Meta: maior ou igual a 99%.

## Lead time real de produção
É o número de dias entre StartDate e EndDate de cada ordem. Use julianday(EndDate) - julianday(StartDate).
Este indicador não tem meta formal. É usado para acompanhar tendência.
