import sqlite3
import re

DB_PATH = "backend/data/nse_stocks.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("SELECT id, answer FROM knowledge_base_entries")
rows = cursor.fetchall()

updated = 0

for kb_id, answer in rows:
    if not answer:
        continue

    cleaned = answer

    # Remove Markdown headings (#, ##, ###, etc.)
    cleaned = re.sub(r'^\s*#{1,6}\s*', '', cleaned, flags=re.MULTILINE)

    # Remove bold (**text**)
    cleaned = re.sub(r'\*\*(.*?)\*\*', r'\1', cleaned)

    # Remove italics (*text*)
    cleaned = re.sub(r'\*(.*?)\*', r'\1', cleaned)

    # Remove inline code (`text`)
    cleaned = re.sub(r'`(.*?)`', r'\1', cleaned)

    # Remove markdown links [text](url) -> text
    cleaned = re.sub(r'\[(.*?)\]\((.*?)\)', r'\1', cleaned)

    # Remove blockquotes (> text)
    cleaned = re.sub(r'^\s*>\s*', '', cleaned, flags=re.MULTILINE)

    # Remove horizontal rules (---, ***, ___)
    cleaned = re.sub(r'^\s*([-*_]){3,}\s*$', '', cleaned, flags=re.MULTILINE)

    # Remove bullet markers
    cleaned = re.sub(r'^\s*[-*+]\s+', '', cleaned, flags=re.MULTILINE)

    # Remove numbered list markers
    cleaned = re.sub(r'^\s*\d+\.\s+', '', cleaned, flags=re.MULTILINE)

    # Remove extra blank lines
    cleaned = re.sub(r'\n\s*\n+', '\n\n', cleaned)

    cleaned = cleaned.strip()

    if cleaned != answer:
        cursor.execute(
            "UPDATE knowledge_base_entries SET answer=? WHERE id=?",
            (cleaned, kb_id)
        )
        updated += 1

conn.commit()

print(f"Cleaned {updated} knowledge base entries.")

conn.close()