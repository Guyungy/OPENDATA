import json

with open("testdoc/test1.md", "r", encoding="utf-8") as f:
    text = f.read()

data = {
  "workspace_id": "testdoc_run",
  "source_type": "document_markdown",
  "origin": "testdoc/test1.md",
  "author": "tester",
  "metadata": {"doc": "test1"},
  "text": text
}

with open("testdoc_run/sources/test1.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
