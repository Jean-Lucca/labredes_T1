#!/bin/bash

# Lista os containers em execução
RUNNING_CONTAINERS=$(podman ps -q)

if [ -z "$RUNNING_CONTAINERS" ]; then
    echo "Nenhum container em execução."
else
    echo "Parando containers..."
    podman stop $RUNNING_CONTAINERS
    echo "Removendo containers..."
    podman rm $RUNNING_CONTAINERS
    echo "Todos os containers foram parados e removidos."
fi
