import duckdb
con = duckdb.connect('C:/Users/jichu/Downloads/hvdc_mail_app/hvdc_mail.duckdb')

total = con.execute('SELECT COUNT(*) FROM emails').fetchone()[0]
print(f'emails rows: {total:,}')

has_emb = con.execute(
    "SELECT COUNT(*) FROM information_schema.columns "
    "WHERE table_name='emails' AND column_name='embedding'"
).fetchone()[0]
print(f'embedding column: {bool(has_emb)}')

if has_emb:
    filled = con.execute('SELECT COUNT(*) FROM emails WHERE embedding IS NOT NULL').fetchone()[0]
    print(f'embeddings filled: {filled:,} / {total:,}')

staging = con.execute(
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_name='emb_staging'"
).fetchone()[0]
print(f'emb_staging exists: {bool(staging)}')
if staging:
    sc = con.execute('SELECT COUNT(*) FROM emb_staging').fetchone()[0]
    print(f'emb_staging rows: {sc:,}')

try:
    indexes = con.execute(
        "SELECT index_name FROM duckdb_indexes() WHERE table_name='emails'"
    ).fetchall()
    print(f'indexes: {[r[0] for r in indexes]}')
except Exception as e:
    print(f'indexes query error: {e}')

con.close()
print('DB OK')
