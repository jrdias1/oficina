@echo off
echo 🔄 Ativando ambiente virtual...

if not exist venv (
    echo 🧪 Criando ambiente virtual...
    python -m venv venv
)

call venv\Scripts\activate

echo 📦 Instalando dependências...
pip install --upgrade pip
pip install flask flask_sqlalchemy flask_login

echo 🚀 Iniciando aplicação...
python main.py

pause
