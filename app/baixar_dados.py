import urllib.request
from pathlib import Path

BASE = ("https://raw.githubusercontent.com/microsoft/sql-server-samples/master/"
        "samples/databases/adventure-works/oltp-install-script/")
ARQUIVOS = [
    "instawdb.sql", "Product.csv", "WorkOrder.csv", "WorkOrderRouting.csv", "BillOfMaterials.csv",
    "ProductInventory.csv", "Location.csv", "ScrapReason.csv", "PurchaseOrderHeader.csv",
    "PurchaseOrderDetail.csv", "Vendor.csv", "ProductVendor.csv",
]


def main():
    pasta = Path("data")
    pasta.mkdir(exist_ok=True)
    for nome in ARQUIVOS:
        destino = pasta / nome
        if destino.exists():
            print(f"já existe: {nome}")
            continue
        print(f"baixando {nome} ...")
        urllib.request.urlretrieve(BASE + nome, destino)
    print("Pronto. Próximo passo: python app\\carregar_dados.py")


if __name__ == "__main__":
    main()