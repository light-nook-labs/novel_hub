from sqlmodel import text
from database import cloud_engine


def list_tables_and_data(engine):
    if not engine:
        print("数据库引擎未配置")
        return

    try:
        with engine.connect() as conn:
            # 1. 查询 public 下所有数据表
            table_sql = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_name;
            """)
            tables = [row.table_name for row in conn.execute(table_sql).all()]

            if not tables:
                print("当前数据库暂无数据表")
                return

            print(f"共 {len(tables)} 张表：")
            # 2. 遍历每张表，查询前20条
            for tbl in tables:
                print(f"\n---------- 表：{tbl} ----------")
                # 查询前20行
                rows = conn.execute(text(f'SELECT * FROM "{tbl}" LIMIT 20;')).all()
                if not rows:
                    print("暂无数据")
                    continue
                # 打印字段名 + 数据
                cols = rows[0]._fields
                print("字段：", cols)
                for idx, r in enumerate(rows, 1):
                    print(f"{idx}. {r}")

    except Exception as e:
        print(f"执行出错：{e}")


if __name__ == "__main__":
    list_tables_and_data(cloud_engine)
