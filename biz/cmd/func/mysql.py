import json
from typing import List, Dict, Any

import pymysql

from biz.cmd.func.base import LLMReviewFunc


class MySQLReviewFunc(LLMReviewFunc):
    SYSTEM_PROMPT = f"""
        你是一个经验丰富的数据库架构专家，擅长MySQL数据库设计评审和性能优化。你在评审数据库结构时会从以下角度进行系统性的分析并提出可操作的建议：
        1. 表结构设计（命名规范、主键设置、字段设计等）
        2. 字段类型是否合理（如金额使用DECIMAL、避免TEXT/BLOB滥用等）
        3. 索引设计（是否有必要索引、冗余索引、联合索引顺序等）
        4. 表与表之间的关系建模（是否正确使用外键、中间表、多对多等）
        5. 性能与容量规划（是否考虑数据量增长、归档、冷热数据等）
        6. 安全性（是否有敏感数据加密、访问控制）
        7. 可维护性与扩展性（命名规范、注释、迁移工具支持等）
        如果发现潜在问题，请指出原因，并建议最佳实践或优化方式。
        """

    def parse_arguments(self):
        """
        使用交互方式获取 MySQL 数据库连接参数。
        """

        def input_with_default(prompt, default=None, required=True, cast_func=None):
            while True:
                value = input(f"{prompt}{f' (默认: {default})' if default else ''}: ").strip()
                if not value:
                    if default is not None:
                        return default
                    if not required:
                        return None
                    print("❌ 该项不能为空")
                    continue
                if cast_func:
                    try:
                        return cast_func(value)
                    except ValueError:
                        print("❌ 输入格式不正确，请重新输入")
                        continue
                return value

        self.host = input_with_default("请输入数据库地址", default="localhost")
        self.port = input_with_default("请输入数据库端口", default=3306, cast_func=int)
        self.user = input_with_default("请输入数据库用户名", default="root")
        self.password = input_with_default("请输入数据库密码", required=True)
        self.database = input_with_default("请输入数据库名称", required=True)
        self.pattern = input_with_default("请输入表名通配符 (支持LIKE语法，如 user%、log_%)，留空表示全部表", required=False)

    def get_prompts(self, text: str) -> List[Dict[str, Any]]:
        self.user_prompt = f"""
            我将提供一份 MySQL 表结构定义，请你根据以上标准进行全面的 review，指出存在的问题并给出优化建议：

            {text}
            """
        return [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": self.user_prompt},
        ]

    def get_mysql_schema(self):
        conn = pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            db=self.database,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )

        schema = {"tables": []}

        try:
            with conn.cursor() as cursor:
                # 获取所有表（根据通配符过滤）
                if self.pattern:
                    cursor.execute(f"SHOW TABLES LIKE %s", (self.pattern,))
                else:
                    cursor.execute(f"SHOW TABLES")

                table_column_name = cursor.description[0][0]
                tables = [row[table_column_name] for row in cursor.fetchall()]

                if not tables:
                    print("⚠️ 未匹配到任何表，请检查通配符或数据库是否正确。")
                    return schema

                for table in tables:
                    # 获取列信息
                    cursor.execute(f"SHOW FULL COLUMNS FROM `{table}`")
                    columns_info = cursor.fetchall()

                    # 获取主键信息
                    cursor.execute(f"""
                        SELECT COLUMN_NAME
                        FROM information_schema.KEY_COLUMN_USAGE
                        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND CONSTRAINT_NAME = 'PRIMARY'
                    """, (self.database, table))
                    primary_keys = {row['COLUMN_NAME'] for row in cursor.fetchall()}

                    # 获取外键信息
                    cursor.execute(f"""
                        SELECT COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
                        FROM information_schema.KEY_COLUMN_USAGE
                        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND REFERENCED_TABLE_NAME IS NOT NULL
                    """, (self.database, table))
                    foreign_keys = {
                        row['COLUMN_NAME']: {
                            "table": row['REFERENCED_TABLE_NAME'],
                            "column": row['REFERENCED_COLUMN_NAME']
                        } for row in cursor.fetchall()
                    }

                    table_dict = {
                        "name": table,
                        "columns": []
                    }

                    for col in columns_info:
                        col_name = col['Field']
                        col_type = col['Type']
                        col_comment = col['Comment']
                        is_primary = col_name in primary_keys
                        foreign_key = foreign_keys.get(col_name)

                        table_dict["columns"].append({
                            "name": col_name,
                            "type": col_type,
                            "primary_key": is_primary,
                            "foreign_key": foreign_key,
                            "comment": col_comment
                        })

                    schema["tables"].append(table_dict)

        finally:
            conn.close()

        return schema

    def process(self):
        self.parse_arguments()
        schema = self.get_mysql_schema()
        if not schema["tables"]:
            print("❌ 未获取到任何表结构，程序退出。")
            return
        text = json.dumps(schema, indent=4, ensure_ascii=False)

        print("即将进行 Review 的表结构如下：\n")
        print(text)  # 打印 review 内容

        if self.confirm_action("是否确认发送 Review 请求？(y/n): "):
            result = self.review_and_strip_code(text)
            print("Review 结果:\n", result)
        else:
            print("用户取消操作，退出程序。")


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv("conf/.env")
    func = MySQLReviewFunc()
    func.process()
