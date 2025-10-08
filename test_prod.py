from app import app, db
from sqlalchemy import inspect, text

with app.app_context():
    print("🔹 Conectando ao banco de produção...")

    # 1️⃣ Listar todas as tabelas
    inspector = inspect(db.engine)
    tabelas = inspector.get_table_names()
    print("Tabelas no banco:", tabelas)

    # 2️⃣ Listar produtos (se existir a tabela 'product')
    if 'product' in tabelas:
        print("\n🔹 Produtos cadastrados:")
        result = db.session.execute(text("SELECT * FROM product"))
        for row in result.mappings():
            print(dict(row))

    else:
        print("\nA tabela 'product' não existe no banco.")
