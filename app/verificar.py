import sqlite3

con = sqlite3.connect("data/pcp.db")

print("Faixa de DueDate:", con.execute("SELECT MIN(DueDate), MAX(DueDate) FROM WorkOrder").fetchone())
print("OPs concluídas após o prazo:", con.execute("SELECT COUNT(*) FROM WorkOrder WHERE date(EndDate) > date(DueDate)").fetchone())
print("Itens de compra / com recebimento menor que o pedido:", con.execute("SELECT COUNT(*), SUM(ReceivedQty < OrderQty) FROM PurchaseOrderDetail").fetchone())
