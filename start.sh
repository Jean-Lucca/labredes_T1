#!/bin/bash

# Verifica argumentos
if [ $# -lt 2 ]; then
    echo "Uso: ./start.sh <porta-local> <nome-container>"
    exit 1
fi

PORT=$1
CONTAINER_NAME=$2

# Inicia o container com nome customizado, substituindo se já existir
podman run -d \
  --replace \
  --name ${CONTAINER_NAME} \
  --cap-add NET_ADMIN \
  --privileged \
  --network lab \
  -p ${PORT}:8080 \
  labredes \
  bash -c "cd /home/ex && python3 main.py"


# Espera um pouco o container subir
sleep 2

# Exemplo: copia um arquivo local para dentro do container
# Altere conforme necessário
podman cp ~/ex ${CONTAINER_NAME}:/home/ex

# Abre o navegador na porta correta
xdg-open http://localhost:${PORT} >/dev/null 2>&1 &
