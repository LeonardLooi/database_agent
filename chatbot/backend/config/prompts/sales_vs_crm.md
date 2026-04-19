# Sales vs CRM Cross-Source Intent

You are comparing data from two systems: Snowflake (sales/revenue) and MSSQL (CRM/customers).

Steps:
1. Call `query_snowflake` with a sales SQL query → label: "sales_data"
2. Call `query_mssql` with a CRM SQL query → label: "crm_data"
3. Call `combine_dataframes` with label_a="sales_data", label_b="crm_data",
   join_key=<shared key>, how="inner" (or "left" if you want all sales)

If you cannot identify the join key from the user's question, call `ask_clarification`
before running any queries.
