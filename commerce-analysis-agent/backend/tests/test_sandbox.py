import duckdb

from app.sandbox import SandboxError, execute_readonly


def test_write_is_rejected_and_rows_are_limited(tmp_path):
    database = tmp_path / "demo.duckdb"
    connection = duckdb.connect(str(database))
    connection.execute("CREATE TABLE ods_orders AS SELECT * FROM range(15)")
    connection.close()

    try:
        execute_readonly(database, "DELETE FROM ods_orders")
        raised = False
    except SandboxError:
        raised = True
    assert raised

    result = execute_readonly(database, "SELECT * FROM ods_orders", limit=10)
    assert len(result["rows"]) == 10
    assert result["truncated"] is True
