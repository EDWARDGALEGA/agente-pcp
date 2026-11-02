import sqlite3
from pathlib import Path

import pandas as pd

DATA = Path("data")
DB = DATA / "pcp.db"

TABELAS = {
    "Product": ["ProductID", "Name", "ProductNumber", "MakeFlag", "FinishedGoodsFlag", "Color", "SafetyStockLevel", "ReorderPoint", "StandardCost", "ListPrice", "Size", "SizeUnitMeasureCode", "WeightUnitMeasureCode", "Weight", "DaysToManufacture", "ProductLine", "Class", "Style", "ProductSubcategoryID", "ProductModelID", "SellStartDate", "SellEndDate", "DiscontinuedDate", "rowguid", "ModifiedDate"],
    "WorkOrder": ["WorkOrderID", "ProductID", "OrderQty", "StockedQty", "ScrappedQty", "StartDate", "EndDate", "DueDate", "ScrapReasonID", "ModifiedDate"],
    "WorkOrderRouting": ["WorkOrderID", "ProductID", "OperationSequence", "LocationID", "ScheduledStartDate", "ScheduledEndDate", "ActualStartDate", "ActualEndDate", "ActualResourceHrs", "PlannedCost", "ActualCost", "ModifiedDate"],
    "BillOfMaterials": ["BillOfMaterialsID", "ProductAssemblyID", "ComponentID", "StartDate", "EndDate", "UnitMeasureCode", "BOMLevel", "PerAssemblyQty", "ModifiedDate"],
    "ProductInventory": ["ProductID", "LocationID", "Shelf", "Bin", "Quantity", "rowguid", "ModifiedDate"],
    "Location": ["LocationID", "Name", "CostRate", "Availability", "ModifiedDate"],
    "ScrapReason": ["ScrapReasonID", "Name", "ModifiedDate"],
    "PurchaseOrderHeader": ["PurchaseOrderID", "RevisionNumber", "Status", "EmployeeID", "VendorID", "ShipMethodID", "OrderDate", "ShipDate", "SubTotal", "TaxAmt", "Freight", "TotalDue", "ModifiedDate"],
    "PurchaseOrderDetail": ["PurchaseOrderID", "PurchaseOrderDetailID", "DueDate", "OrderQty", "ProductID", "UnitPrice", "LineTotal", "ReceivedQty", "RejectedQty", "StockedQty", "ModifiedDate"],
    "Vendor": ["BusinessEntityID", "AccountNumber", "Name", "CreditRating", "PreferredVendorStatus", "ActiveFlag", "PurchasingWebServiceURL", "ModifiedDate"],
    "ProductVendor": ["ProductID", "BusinessEntityID", "AverageLeadTime", "StandardPrice", "LastReceiptCost", "LastReceiptDate", "MinOrderQty", "MaxOrderQty", "OnOrderQty", "UnitMeasureCode", "ModifiedDate"],
}


def carregar():
    con = sqlite3.connect(DB)
    for nome, colunas in TABELAS.items():
        df = pd.read_csv(
            DATA / f"{nome}.csv",
            sep="\t",
            header=None,
            names=colunas,
            keep_default_na=False,
            na_values=[""],
        )
        df.to_sql(nome, con, if_exists="replace", index=False)
        print(f"{nome}: {len(df)} linhas")
    con.close()


if __name__ == "__main__":
    carregar()