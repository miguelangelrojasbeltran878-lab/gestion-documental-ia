import os

main_path = r'c:\Users\Lenovo\OneDrive\Documentos\Proyecto_Aplicaciones_Empresariales\03_Desarrollo\app\main.py'
with open(main_path, 'r', encoding='utf-8') as f:
    code = f.read()

# Add json and datetime to top of main.py if missing
if 'import json' not in code:
    code = 'import json\nfrom datetime import datetime\n' + code

# In post_login, ensure datetime is available
if 'agente.ultimo_acceso = datetime.utcnow()' in code and 'from datetime import datetime' not in code:
    code = 'from datetime import datetime\n' + code

with open(main_path, 'w', encoding='utf-8') as f:
    f.write(code)

print("Imports in main.py fixed successfully!")
